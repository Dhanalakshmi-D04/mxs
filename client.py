"""
client.py
=========
Typed HTTP client for CodeReviewEnv.
Agents use this to connect to the running HF Space.

Usage (async):
    from code_review_env import CodeReviewEnv, CodeReviewAction
    async with CodeReviewEnv(base_url="https://your-space.hf.space") as env:
        result = await env.reset()
        result = await env.step(CodeReviewAction(action_type="comment", ...))

Usage (sync):
    with CodeReviewEnv(base_url="https://your-space.hf.space").sync() as env:
        result = env.reset()
        result = env.step(CodeReviewAction(action_type="submit", final_summary="done"))
"""

try:
    from openenv.core.http_env_client import HTTPEnvClient
    from models import CodeReviewAction, CodeReviewObservation

    class CodeReviewEnv(HTTPEnvClient[CodeReviewAction, CodeReviewObservation]):
        """Typed client for CodeReviewEnv."""
        pass

except ImportError:
    # Fallback stub so inference.py can import without openenv-core installed
    class CodeReviewEnv:  # type: ignore
        def __init__(self, base_url: str = ""):
            self.base_url = base_url

        def __repr__(self):
            return f"CodeReviewEnv(base_url={self.base_url!r})"