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


def _has_fix(actions: List[CodeReviewAction]) -> bool:
    return any(a.action_type == "fix" and a.fixed_content for a in actions)


def _get_comments(actions):
    return [a for a in actions if a.action_type == "comment"]


def grade_easy(actions: List[CodeReviewAction], final_code: str) -> dict:
    comments = _get_comments(actions)
    comment = comments[0] if comments else None

    # Fail=0.02, Pass values scaled to ensure max sum ~0.65
    commented    = 0.09 if comment else 0.02
    correct_line = 0.13 if (comment and comment.line_number == 5) else 0.02
    good_comment = 0.13 if (comment and comment.comment_text and
                             len(comment.comment_text) > 10) else 0.02
    valid_syntax = 0.09 if _valid_syntax(final_code) else 0.02
    fix_present  = 0.21 if _has_fix(actions) else 0.02

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.02*5 = 0.10, Max = 0.09+0.13+0.13+0.09+0.21 = 0.65
    return {
        "total": round(total, 4),
        "breakdown": {
            "commented": commented,
            "correct_line": correct_line,
            "good_comment": good_comment,
            "valid_syntax": valid_syntax,
            "fix_present": fix_present,
        }
    }


def grade_medium(actions: List[CodeReviewAction], final_code: str) -> dict:
    comments = _get_comments(actions)
    comment = comments[0] if comments else None

    # Scaled down to ensure max sum ~0.60
    commented    = 0.08 if comment else 0.02
    correct_line = 0.12 if (comment and comment.line_number in [3, 4, 5]) else 0.02
    good_comment = 0.12 if (comment and comment.comment_text and
                              len(comment.comment_text) > 10) else 0.02
    valid_syntax = 0.08 if _valid_syntax(final_code) else 0.02
    fix_present  = 0.20 if _has_fix(actions) else 0.02

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.10, Max = 0.60
    return {
        "total": round(total, 4),
        "breakdown": {
            "commented": commented,
            "correct_line": correct_line,
            "good_comment": good_comment,
            "valid_syntax": valid_syntax,
            "fix_present": fix_present,
        }
    }


def grade_hard(actions: List[CodeReviewAction], final_code: str) -> dict:
    comments = _get_comments(actions)
    comment = comments[0] if comments else None

    # Scaled down to ensure max sum ~0.55
    commented    = 0.07 if comment else 0.02
    correct_line = 0.11 if (comment and comment.line_number) else 0.02
    good_comment = 0.11 if (comment and comment.comment_text and
                              len(comment.comment_text) > 15) else 0.02
    valid_syntax = 0.07 if _valid_syntax(final_code) else 0.02
    fix_present  = 0.19 if _has_fix(actions) else 0.02

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.10, Max = 0.55
    return {
        "total": round(total, 4),
        "breakdown": {
            "commented": commented,
            "correct_line": correct_line,
            "good_comment": good_comment,
            "valid_syntax": valid_syntax,
            "fix_present": fix_present,
        }
    }
GRADERS = {
    "task_easy": grade_easy,
    "task_medium": grade_medium,
    "task_hard": grade_hard,
}