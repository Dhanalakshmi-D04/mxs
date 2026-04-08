import ast
from typing import List

try:
    from ..models import CodeReviewAction
except ImportError:
    from models import CodeReviewAction


def _valid_syntax(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _uses_parameterized_query(code: str) -> bool:
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


def _s(val: float) -> float:
    """Clamp a single score component to strictly (0, 1)."""
    return round(min(0.99, max(0.01, val)), 4)


def grade_easy(actions: List[CodeReviewAction], final_code: str) -> dict:
    comments = [a for a in actions if a.action_type == "comment"]
    all_text = _all_comments(actions)

    commented    = _s(0.14 if comments else 0.01)
    correct_line = _s(0.20 if any(a.line_number in [5, 6] for a in comments) else 0.01)
    good_comment = _s(0.20 if any(k in all_text for k in ["empty", "zero", "division", "len"]) else 0.01)

    fix_kw = ["if not numbers", "if len(numbers) == 0", "if len(numbers) < 1",
               "return 0", "return none", "return 0.0"]
    has_fix = any(k in final_code.lower() for k in fix_kw)

    if _valid_syntax(final_code):
        valid_syntax = _s(0.15)
        fix_present  = _s(0.30 if has_fix else 0.01)
    else:
        valid_syntax = _s(0.01)
        fix_present  = _s(0.01)

    s = {
        "commented":    commented,
        "correct_line": correct_line,
        "good_comment": good_comment,
        "valid_syntax": valid_syntax,
        "fix_present":  fix_present,
    }
    total = _s(sum(s.values()) / (len(s) * 0.99) * 0.90)
    return {"total": total, "breakdown": s}


def grade_medium(actions: List[CodeReviewAction], final_code: str) -> dict:
    comments = [a for a in actions if a.action_type == "comment"]

    bug1_found = _s(0.10 if any(a.line_number in [2, 3] for a in comments) else 0.01)
    bug2_found = _s(0.10 if any(a.line_number in [4, 5] for a in comments) else 0.01)

    fix1 = "len(arr) - 1" in final_code
    fix2 = "//" in final_code

    if _valid_syntax(final_code):
        valid_syntax  = _s(0.15)
        fix_offbyone  = _s(0.20 if fix1 else 0.01)
        fix_intdiv    = _s(0.20 if fix2 else 0.01)
    else:
        valid_syntax = fix_offbyone = fix_intdiv = _s(0.01)

    both_bonus = _s(0.25 if (fix1 and fix2) else 0.01)

    s = {
        "bug1_found":   bug1_found,
        "bug2_found":   bug2_found,
        "valid_syntax": valid_syntax,
        "fix_offbyone": fix_offbyone,
        "fix_intdiv":   fix_intdiv,
        "both_bonus":   both_bonus,
    }
    total = _s(sum(s.values()) / (len(s) * 0.99) * 0.90)
    return {"total": total, "breakdown": s}


def grade_hard(actions: List[CodeReviewAction], final_code: str) -> dict:
    text = _all_comments(actions)
    code = final_code.lower()

    sql_found       = _s(0.10 if ("sql" in text or "injection" in text) else 0.01)
    timing_found    = _s(0.10 if ("timing" in text or "compare_digest" in text) else 0.01)
    plaintext_found = _s(0.10 if ("plaintext" in text or "hash" in text or "bcrypt" in text) else 0.01)

    param_ok = _uses_parameterized_query(final_code) and not _fstring_in_execute(final_code)
    param_query    = _s(0.25 if param_ok else 0.01)
    secure_compare = _s(0.20 if "compare_digest" in code else 0.01)

    pw_hashing = _s(0.20 if (
        "bcrypt" in code
        or "pbkdf2" in code
        or ("hashlib" in code and ("sha256" in code or "sha512" in code))
    ) else 0.01)

    has_fstring_penalty = _fstring_in_execute(final_code)
    has_injection_penalty = ("f'" in final_code and "username" in final_code and "select" in code)

    s = {
        "sql_found":       sql_found,
        "timing_found":    timing_found,
        "plaintext_found": plaintext_found,
        "param_query":     param_query,
        "secure_compare":  secure_compare,
        "pw_hashing":      pw_hashing,
    }

    raw = sum(s.values())
    if has_fstring_penalty:
        raw -= 0.29
    if has_injection_penalty:
        raw -= 0.19

    total = _s(raw / (len(s) * 0.99) * 0.90)
    return {"total": total, "breakdown": s}


GRADERS = {
    "task_easy":   grade_easy,
    "task_medium": grade_medium,
    "task_hard":   grade_hard,
}