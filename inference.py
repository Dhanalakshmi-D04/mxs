"""
inference.py
============
CodeReviewEnv baseline inference script.

Mandatory stdout format (judges parse this exactly):
  [START] task=<task_id> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> rewards=<r1,r2,...>

Required env variables:
  HF_TOKEN       Your Hugging Face / API key
  API_BASE_URL   LLM endpoint  (default: HuggingFace router)
  MODEL_NAME     Model identifier (default: Qwen/Qwen2.5-72B-Instruct)
"""

import asyncio
import json
import os
import signal
import sys
import textwrap
from typing import List, Optional

from openai import OpenAI

# ── Import environment (works from project root) ───────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server.code_review_environment import CodeReviewEnvironment
from models import CodeReviewAction

# ── Configuration ──────────────────────────────────────────────────────────────
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK    = "code-review-env"
ALL_TASKS    = ["task_easy", "task_medium", "task_hard"]
MAX_STEPS    = 8
TEMPERATURE  = 0.2
MAX_TOKENS   = 1500
SUCCESS_THRESHOLD = 0.5

# ── 18-min hard timeout (2-min buffer under the 20-min limit) ─────────────────
def _on_timeout(signum, frame):
    print("\n[END] success=false steps=0 rewards=", flush=True)
    sys.exit(1)

if hasattr(signal, "SIGALRM"):
    signal.signal(signal.SIGALRM, _on_timeout)
    signal.alarm(18 * 60)


# ── Mandatory stdout loggers ───────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float,
             done: bool, error: Optional[str]) -> None:
    action_str = action.replace("\n", " ").replace("\r", "")[:120]
    done_str   = str(done).lower()
    err_str    = error if error else "null"
    print(
        f"[STEP] step={step} action={action_str} "
        f"reward={reward:.2f} done={done_str} error={err_str}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    r_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={r_str}",
        flush=True,
    )


# ── Prompts ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are a senior Python code reviewer inside a structured environment.
    Each turn respond with exactly ONE valid JSON object — no prose, no markdown fences.

    Available action types:

    1. Identify a bug:
       {"action_type": "comment", "line_number": <int>, "comment_text": "<explanation + severity>"}

    2. Submit corrected file:
       {"action_type": "fix", "filename": "<filename>", "fixed_content": "<full corrected file>"}

    3. End the episode:
       {"action_type": "submit", "final_summary": "<summary of all bugs found and fixed>"}

    Order: comment (one per bug) -> fix -> submit.

    Security rules (for auth tasks):
      - SQL: use cursor.execute(query, (param,)) with a '?' placeholder — never f-strings.
      - Comparison: use hmac.compare_digest() — never plain ==.
      - Passwords: use hashlib.pbkdf2_hmac or bcrypt — never plaintext.

    One JSON object per response. Nothing else.
""").strip()


def _user_prompt(task_desc: str, code_files: list, feedback: list, step: int) -> str:
    code_block = "\n\n".join(
        f"### {f.filename}\n```python\n{f.content}\n```"
        for f in code_files
    )
    fb = "\n".join(feedback[-6:]) if feedback else "None yet."
    return textwrap.dedent(f"""
        Task:
        {task_desc}

        Code to review:
        {code_block}

        Actions so far (step {step}):
        {fb}

        Respond with your next JSON action.
    """).strip()


# ── Model call ─────────────────────────────────────────────────────────────────

def call_model(client: OpenAI, task_desc: str, code_files: list,
               feedback: list, step: int) -> tuple:
    """Returns (action_dict, error_or_None)."""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": _user_prompt(task_desc, code_files, feedback, step)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (resp.choices[0].message.content or "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return {"action_type": "submit", "final_summary": "JSON parse error"}, str(e)
    except Exception as e:
        return {"action_type": "submit", "final_summary": "model error"}, str(e)


# ── Episode loop ───────────────────────────────────────────────────────────────

def run_task(task_id: str, client: OpenAI) -> float:
    env = CodeReviewEnvironment(task_id=task_id)
    obs = env.reset()

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        for step in range(1, MAX_STEPS + 1):
            if obs.done:
                break

            action_dict, model_err = call_model(
                client, obs.task_description, obs.code_files,
                obs.current_feedback, step,
            )

            try:
                action = CodeReviewAction(**action_dict)
                parse_err = None
            except Exception as e:
                parse_err = str(e)
                action = CodeReviewAction(
                    action_type="submit",
                    final_summary=f"parse error: {parse_err}",
                )

            error_msg = model_err or parse_err

            obs = env.step(action)
            reward_info = env._last_reward_info
            reward_val  = reward_info.value
            rewards.append(reward_val)
            steps_taken = step

            log_step(
                step=step,
                action=json.dumps(action_dict)[:120],
                reward=reward_val,
                done=obs.done,
                error=error_msg,
            )

            if obs.done:
                score   = reward_val
                success = score >= SUCCESS_THRESHOLD
                break

    except Exception as exc:
        print(f"[DEBUG] episode error: {exc}", flush=True)
        score   = rewards[-1] if rewards else 0.05
        success = False

    finally:
        if not (0.0 < score < 1.0):
            score = 0.05
        log_end(success=success, steps=steps_taken, rewards=rewards)

    return score


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    if not API_KEY:
        print("[ERROR] Set HF_TOKEN or API_KEY environment variable.", flush=True)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    task_env = os.getenv("TASK_NAME", "all")
    tasks    = ALL_TASKS if task_env == "all" else [task_env]
    results  = {}

    for task_id in tasks:
        results[task_id] = run_task(task_id, client)
        print("", flush=True)

    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)

    # Summary to stderr — does not pollute the required stdout format
    print("\n-- summary --", file=sys.stderr)
    for tid, s in results.items():
        bar = "#" * int(s * 20)
        print(f"  {tid:<15} {s:.3f}  {bar}", file=sys.stderr)
    if results:
        avg = sum(results.values()) / len(results)
        print(f"  {'average':<15} {avg:.3f}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())