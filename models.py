from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

try:
    from openenv.core.env_server.types import (
        Action as BaseAction,
        Observation as BaseObservation,
    )
    _USE_OPENENV_TYPES = True
except ImportError:
    _USE_OPENENV_TYPES = False


# ── Nested data (plain Pydantic, not an OpenEnv type) ─────────────────────────

class CodeFile(BaseModel):
    filename: str
    content: str
    language: str = "python"


# ── Action ────────────────────────────────────────────────────────────────────

if _USE_OPENENV_TYPES:
    class CodeReviewAction(BaseAction):
        action_type: str = Field(
            ..., description="One of: 'comment', 'fix', 'submit'"
        )
        line_number: Optional[int] = Field(
            None, description="Line where the bug was found (comment actions)"
        )
        comment_text: Optional[str] = Field(
            None, description="Explanation of the bug (comment actions)"
        )
        filename: Optional[str] = Field(
            None, description="File to fix (fix actions)"
        )
        fixed_content: Optional[str] = Field(
            None, description="Entire corrected file content (fix actions)"
        )
        final_summary: Optional[str] = Field(
            None, description="Summary of all changes (submit actions)"
        )
else:
    class CodeReviewAction(BaseModel):
        action_type: str = Field(...)
        line_number: Optional[int] = None
        comment_text: Optional[str] = None
        filename: Optional[str] = None
        fixed_content: Optional[str] = None
        final_summary: Optional[str] = None


# ── Observation ───────────────────────────────────────────────────────────────

if _USE_OPENENV_TYPES:
    class CodeReviewObservation(BaseObservation):
        task_id: str
        task_description: str
        code_files: List[CodeFile]
        current_feedback: List[str]
        tests_passed: int
        tests_total: int
        step_count: int
        done: bool
else:
    class CodeReviewObservation(BaseModel):
        task_id: str
        task_description: str
        code_files: List[CodeFile]
        current_feedback: List[str]
        tests_passed: int
        tests_total: int
        step_count: int
        done: bool


# ── Reward (plain Pydantic — not an OpenEnv type) ─────────────────────────────

class RewardInfo(BaseModel):
    value: float = Field(..., gt=0.0, lt=1.0)
    breakdown: Dict[str, Any]
    message: str