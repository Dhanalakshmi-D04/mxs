import ast
from typing import List

try:
    from ..models import CodeReviewAction
except ImportError:
    from models import CodeReviewAction


# ── AST helpers ────────────────────────────────────────────────────────────────

def _valid_syntax(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _uses_parameterized_query(code: str) -> bool:
    """True only if cursor.execute() is called with 2 args (query + params tuple)."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "execute":
                    if len(node.args) >= 2:
                        return True
        return False
    except SyntaxError:
        return False


def _fstring_in_execute(code: str) -> bool:
    """True (bad) if an f-string is passed directly into execute()."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "execute":
                    for arg in node.args:
                        if isinstance(arg, ast.JoinedStr):
                            return True
        return False
    except SyntaxError:
        return False


def _all_comments(actions: List[CodeReviewAction]) -> str:
    return " ".join(
        (a.comment_text or "") for a in actions if a.action_type == "comment"
    ).lower()


# ── Graders ────────────────────────────────────────────────────────────────────

def grade_easy(actions: List[CodeReviewAction], final_code: str) -> dict:
    """
    Max 1.0:
      +0.15  any comment submitted
      +0.20  correct line number cited (5 or 6)
      +0.20  comment mentions the cause (empty/zero/division/len)
      +0.30  fix contains a proper guard clause
      +0.15  fixed code is syntactically valid
    """
    s = {}
    comments = [a for a in actions if a.action_type == "comment"]
    all_text = _all_comments(actions)

    s["commented"]     = 0.15 if comments else 0.0
    s["correct_line"]  = 0.20 if any(a.line_number in [5, 6] for a in comments) else 0.0
    s["good_comment"]  = 0.20 if any(k in all_text for k in ["empty", "zero", "division", "len"]) else 0.0

    fix_kw = ["if not numbers", "if len(numbers) == 0", "if len(numbers) < 1",
               "return 0", "return none", "return 0.0"]
    has_fix = any(k in final_code.lower() for k in fix_kw)

    if _valid_syntax(final_code):
        s["valid_syntax"] = 0.15
        s["fix_present"]  = 0.30 if has_fix else 0.0
    else:
        s["valid_syntax"] = 0.0
        s["fix_present"]  = 0.0   # broken syntax voids fix score

    return {"total": round(min(1.0, sum(s.values())), 4), "breakdown": s}


def grade_medium(actions: List[CodeReviewAction], final_code: str) -> dict:
    """
    Max 1.0:
      +0.10  bug 1 identified (line 2/3)
      +0.10  bug 2 identified (line 4/5)
      +0.20  fix contains len(arr) - 1
      +0.20  fix uses integer division //
      +0.15  code is syntactically valid
      +0.25  bonus: both fixes present together
    """
    s = {}
    comments = [a for a in actions if a.action_type == "comment"]

    s["bug1_found"] = 0.10 if any(a.line_number in [2, 3] for a in comments) else 0.0
    s["bug2_found"] = 0.10 if any(a.line_number in [4, 5] for a in comments) else 0.0

    fix1 = "len(arr) - 1" in final_code
    fix2 = "//" in final_code

    if _valid_syntax(final_code):
        s["valid_syntax"]  = 0.15
        s["fix_offbyone"]  = 0.20 if fix1 else 0.0
        s["fix_intdiv"]    = 0.20 if fix2 else 0.0
    else:
        s["valid_syntax"] = s["fix_offbyone"] = s["fix_intdiv"] = 0.0

    s["both_bonus"] = 0.25 if (fix1 and fix2) else 0.0

    return {"total": round(min(1.0, sum(s.values())), 4), "breakdown": s}


def grade_hard(actions: List[CodeReviewAction], final_code: str) -> dict:
    """
    Max 1.0:
      +0.10  SQL injection identified in comment
      +0.10  timing attack identified in comment
      +0.10  plaintext password identified in comment
      +0.25  fix uses parameterized query (AST-verified)
      +0.20  fix uses hmac.compare_digest
      +0.20  fix uses password hashing (hashlib/bcrypt/pbkdf2)
      -0.30  penalty: f-string still in execute() call
      -0.20  penalty: f-string + username + select still present
    """
    s = {}
    text = _all_comments(actions)
    code = final_code.lower()

    s["sql_found"]      = 0.10 if ("sql" in text or "injection" in text) else 0.0
    s["timing_found"]   = 0.10 if ("timing" in text or "compare_digest" in text) else 0.0
    s["plaintext_found"]= 0.10 if ("plaintext" in text or "hash" in text or "bcrypt" in text) else 0.0

    param_ok = _uses_parameterized_query(final_code) and not _fstring_in_execute(final_code)
    s["param_query"]    = 0.25 if param_ok else 0.0

    s["secure_compare"] = 0.20 if "compare_digest" in code else 0.0

    s["pw_hashing"] = 0.20 if (
        "bcrypt" in code
        or "pbkdf2" in code
        or ("hashlib" in code and ("sha256" in code or "sha512" in code))
    ) else 0.0

    # Penalties
    s["penalty_fstring"]   = -0.30 if _fstring_in_execute(final_code) else 0.0
    s["penalty_injection"] = -0.20 if (
        "f'" in final_code and "username" in final_code and "select" in code
    ) else 0.0

    return {"total": round(max(0.0, min(1.0, sum(s.values()))), 4), "breakdown": s}


GRADERS = {
    "task_easy":   grade_easy,
    "task_medium": grade_medium,
    "task_hard":   grade_hard,
}