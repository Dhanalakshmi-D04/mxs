import uuid
from typing import List, Tuple, Dict, Any

try:
    from openenv.core.env_server.interfaces import Environment
    from openenv.core.env_server.types import State
    _HAS_OPENENV = True
except ImportError:
    _HAS_OPENENV = False
    Environment = object
    State = None

try:
    from models import CodeReviewAction, CodeReviewObservation, CodeFile, RewardInfo
    from ..server.tasks import TASKS
    from ..server.grader import GRADERS
except ImportError:
    from models import CodeReviewAction, CodeReviewObservation, CodeFile, RewardInfo
    from server.tasks import TASKS
    from server.grader import GRADERS


class CodeReviewEnvironment(Environment):
    """
    OpenEnv Environment for AI code review.

    Supports 3 tasks: task_easy, task_medium, task_hard.
    Episode ends when agent submits or MAX_STEPS is reached.
    """

    MAX_STEPS = 10

    def __init__(self, task_id: str = "task_easy"):
        if _HAS_OPENENV:
            super().__init__()
        if task_id not in TASKS:
            raise ValueError(f"Unknown task_id '{task_id}'. Valid: {list(TASKS.keys())}")
        self.task_id = task_id
        self._task = TASKS[task_id]
        self._episode_id: str = ""
        self._actions: List[CodeReviewAction] = []
        self._current_files: List[CodeFile] = []
        self._step_count: int = 0
        self._done: bool = False
        self._cumulative_reward: float = 0.0

    # ── OpenEnv required methods ───────────────────────────────────────────────

    def reset(self) -> CodeReviewObservation:
        """Initialise a fresh episode and return the first observation."""
        self._episode_id = str(uuid.uuid4())
        self._actions = []
        self._current_files = [
            CodeFile(filename=f.filename, content=f.content, language=f.language)
            for f in self._task["files"]
        ]
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0
        return self._make_obs()

    def step(self, action: CodeReviewAction) -> CodeReviewObservation:
        """
        Apply one action and return the next observation.
        Reward and done are embedded in the observation for OpenEnv compatibility.
        Full reward info is also stored in _last_reward_info for the HTTP layer.
        """
        if self._done:
            raise RuntimeError("Episode is finished. Call reset() to start a new one.")

        self._step_count += 1
        self._actions.append(action)

        # Apply fix: update stored file content
        if action.action_type == "fix" and action.filename and action.fixed_content:
            for i, f in enumerate(self._current_files):
                if f.filename == action.filename:
                    self._current_files[i] = CodeFile(
                        filename=f.filename,
                        content=action.fixed_content,
                        language=f.language,
                    )

        terminal = (
            action.action_type == "submit"
            or self._step_count >= self.MAX_STEPS
        )

        if terminal:
            self._done = True
            final_code = self._current_files[0].content if self._current_files else ""
            result = GRADERS[self.task_id](self._actions, final_code)
            reward_val = float(result["total"])
            self._last_reward_info = RewardInfo(
                value=reward_val,
                breakdown=result["breakdown"],
                message=f"Final graded score: {reward_val:.4f}",
            )
        else:
            partial = self._partial_reward(action)
            self._last_reward_info = RewardInfo(
                value=partial,
                breakdown={"step_reward": partial, "action_type": action.action_type},
                message=f"Step {self._step_count} partial reward: {partial:.4f}",
            )

        self._cumulative_reward = round(
            self._cumulative_reward + self._last_reward_info.value, 4
        )
        return self._make_obs()

    @property
    def state(self):
        """Return current episode state (OpenEnv State or plain dict fallback)."""
        if _HAS_OPENENV and State is not None:
            return State(
                episode_id=self._episode_id,
                step_count=self._step_count,
            )
        return {
            "episode_id": self._episode_id,
            "task_id": self.task_id,
            "step_count": self._step_count,
            "max_steps": self.MAX_STEPS,
            "done": self._done,
            "cumulative_reward": self._cumulative_reward,
            "actions_taken": len(self._actions),
            "action_types": [a.action_type for a in self._actions],
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _partial_reward(self, action: CodeReviewAction) -> float:
        """
        Mid-episode signal so the agent learns from every step, not just the end.
          comment + line_number  → +0.08
          comment + good text    → +0.07
          fix with content       → +0.10
          empty comment          → −0.05  (penalise spam)
          repeated fix           → −0.03
        """
        p = 0.0
        if action.action_type == "comment":
            if action.line_number is not None:
                p += 0.08
            if action.comment_text and len(action.comment_text.strip()) > 20:
                p += 0.07
            if not action.comment_text or len(action.comment_text.strip()) < 5:
                p -= 0.05
        elif action.action_type == "fix":
            if action.fixed_content and len(action.fixed_content.strip()) > 50:
                p += 0.10
            # penalise re-fixing without commenting in between
            prev_types = [a.action_type for a in self._actions[:-1]]
            if prev_types and prev_types[-1] == "fix":
                p -= 0.03
        return round(max(0.0, p), 4)

    def _make_obs(self) -> CodeReviewObservation:
        feedback = []
        for i, a in enumerate(self._actions):
            if a.action_type == "comment":
                feedback.append(
                    f"Step {i+1} [comment] line={a.line_number}: "
                    f"{a.comment_text or '(empty)'}"
                )
            elif a.action_type == "fix":
                feedback.append(
                    f"Step {i+1} [fix] {a.filename}: "
                    f"{len(a.fixed_content or '')} chars"
                )
            elif a.action_type == "submit":
                feedback.append(
                    f"Step {i+1} [submit]: {a.final_summary or '(no summary)'}"
                )

        return CodeReviewObservation(
            task_id=self.task_id,
            task_description=self._task["description"],
            code_files=self._current_files,
            current_feedback=feedback,
            tests_passed=0,
            tests_total=len(self._task.get("tests", [])),
            step_count=self._step_count,
            done=self._done,
        )