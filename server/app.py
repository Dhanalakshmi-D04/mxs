"""
server/app.py
=============
FastAPI application for CodeReviewEnv.
Uses openenv.core.env_server.create_fastapi_app when openenv-core is installed.
Falls back to manual FastAPI routes so the server still works during local dev.
"""

import uvicorn


try:
    from ..models import CodeReviewAction, CodeReviewObservation
    from ..server.code_review_environment import CodeReviewEnvironment
except ImportError:
    from models import CodeReviewAction, CodeReviewObservation
    from server.code_review_environment import CodeReviewEnvironment

try:
    from openenv.core.env_server import create_fastapi_app
    app = create_fastapi_app(
        CodeReviewEnvironment,
        CodeReviewAction,
        CodeReviewObservation,
    )

except ImportError:
    # ── Manual FastAPI fallback (works without openenv-core) ──────────────────
    from fastapi import FastAPI, Body
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="CodeReviewEnv", version="1.0.0")

    # one env instance per task_id + __last__ for bare /reset /step /state calls
    _envs: dict = {}

    @app.get("/", response_class=HTMLResponse)
    def root():
        return """
        <h2>CodeReviewEnv is live</h2>
        <ul>
          <li>POST /reset — start episode (body: {"task_id": "task_easy"})</li>
          <li>POST /step  — take an action</li>
          <li>GET  /state — current state</li>
          <li>GET  /tasks — list tasks</li>
          <li>GET  /health — health check</li>
        </ul>
        """

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # ── /reset ─────────────────────────────────────────────────────────────────

    @app.post("/reset")
    def reset_bare(body: dict = Body(default={})):
        """Validator hits: POST /reset with body {}"""
        return _do_reset(body.get("task_id", "task_easy"))

    @app.post("/reset/{task_id}")
    def reset_task(task_id: str):
        return _do_reset(task_id)

    def _do_reset(task_id: str):
        env = CodeReviewEnvironment(task_id=task_id)
        _envs[task_id] = env
        _envs["__last__"] = env
        obs = env.reset()
        return obs.model_dump()

    # ── /step ──────────────────────────────────────────────────────────────────

    @app.post("/step")
    def step_bare(action: CodeReviewAction):
        env = _envs.get("__last__")
        if not env:
            return {"error": "Call POST /reset first"}
        return _do_step(env, action)

    @app.post("/step/{task_id}")
    def step_task(task_id: str, action: CodeReviewAction):
        env = _envs.get(task_id)
        if not env:
            return {"error": f"Call POST /reset/{task_id} first"}
        return _do_step(env, action)

    def _do_step(env: CodeReviewEnvironment, action: CodeReviewAction):
        try:
            obs = env.step(action)
            reward = env._last_reward_info
            return {
                "observation": obs.model_dump(),
                "reward": reward.model_dump(),
                "done": obs.done,
                "info": {"step": obs.step_count},
            }
        except RuntimeError as e:
            return {"error": str(e)}

    # ── /state ─────────────────────────────────────────────────────────────────

    @app.get("/state")
    def state_bare():
        env = _envs.get("__last__")
        if not env:
            return {"error": "Call POST /reset first"}
        return env.state if isinstance(env.state, dict) else env.state.model_dump()

    @app.get("/state/{task_id}")
    def state_task(task_id: str):
        env = _envs.get(task_id)
        if not env:
            return {"error": f"Call POST /reset/{task_id} first"}
        s = env.state
        return s if isinstance(s, dict) else s.model_dump()

    # ── /tasks ─────────────────────────────────────────────────────────────────

    @app.get("/tasks")
    def list_tasks():
        from server.tasks import TASKS
        return {
            "tasks": [
                {
                    "id": tid,
                    "difficulty": {
                        "task_easy": "easy",
                        "task_medium": "medium",
                        "task_hard": "hard",
                    }.get(tid, "unknown"),
                    "description": t["description"][:120] + "...",
                    "num_bugs": len(t["bugs"]),
                }
                for tid, t in TASKS.items()
            ]
        }
    def main():
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()