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

    # Fail=0.05, Pass=chosen so max sum = 0.89 (never hits 1.0)
    commented   = 0.13 if comment else 0.05
    correct_line = 0.18 if (comment and comment.line_number == 5) else 0.05
    good_comment = 0.18 if (comment and comment.comment_text and
                             len(comment.comment_text) > 10) else 0.05
    valid_syntax = 0.13 if _valid_syntax(final_code) else 0.05
    fix_present  = 0.27 if _has_fix(actions) else 0.05

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.05*5 = 0.25, Max = 0.13+0.18+0.18+0.13+0.27 = 0.89
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

    commented    = 0.12 if comment else 0.05
    correct_line = 0.17 if (comment and comment.line_number in [3, 4, 5]) else 0.05
    good_comment = 0.17 if (comment and comment.comment_text and
                              len(comment.comment_text) > 10) else 0.05
    valid_syntax = 0.12 if _valid_syntax(final_code) else 0.05
    fix_present  = 0.25 if _has_fix(actions) else 0.05

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.25, Max = 0.83
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

    commented    = 0.11 if comment else 0.05
    correct_line = 0.16 if (comment and comment.line_number) else 0.05
    good_comment = 0.16 if (comment and comment.comment_text and
                              len(comment.comment_text) > 15) else 0.05
    valid_syntax = 0.11 if _valid_syntax(final_code) else 0.05
    fix_present  = 0.23 if _has_fix(actions) else 0.05

    total = commented + correct_line + good_comment + valid_syntax + fix_present
    # Min = 0.25, Max = 0.77
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