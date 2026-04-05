try:
    from ..models import CodeFile
except ImportError:
    from models import CodeFile


TASKS = {
    "task_easy": {
        "description": (
            "Review this Python function. It has ONE bug that causes a ZeroDivisionError "
            "when an empty list is passed.\n\n"
            "Workflow:\n"
            "1. Send a 'comment' action - include line_number and comment_text explaining the bug.\n"
            "2. Send a 'fix' action - include filename and fixed_content (the entire corrected file).\n"
            "3. Send a 'submit' action - include final_summary.\n\n"
            "Scoring: partial credit given at each step."
        ),
        "files": [
            CodeFile(
                filename="calculate.py",
                content="""\
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


def main():
    data = [10, 20, 30]
    print(calculate_average(data))
    print(calculate_average([]))


main()
""",
            )
        ],
        "bugs": [
            {
                "line": 5,
                "type": "zero_division",
                "description": "ZeroDivisionError when numbers is empty",
            }
        ],
        "tests": [
            {"input": "[10,20,30]", "expected": "20.0"},
            {"input": "[]", "expected": "0 or None"},
        ],
    },

    "task_medium": {
        "description": (
            "This binary search function has 2 bugs:\n"
            "  Bug 1 (line 2): right boundary is len(arr) - should be len(arr) - 1.\n"
            "  Bug 2 (line 4): mid uses float division '/' - should be integer division '//'.\n\n"
            "Workflow:\n"
            "1. Send one 'comment' action per bug (with line_number + comment_text).\n"
            "2. Send a 'fix' action with the fully corrected file.\n"
            "3. Send a 'submit' action with final_summary."
        ),
        "files": [
            CodeFile(
                filename="search.py",
                content="""\
def binary_search(arr, target):
    left, right = 0, len(arr)
    while left <= right:
        mid = (left + right) / 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
""",
            )
        ],
        "bugs": [
            {"line": 2, "type": "off_by_one", "description": "right should be len(arr)-1"},
            {"line": 4, "type": "float_division", "description": "mid must use // not /"},
        ],
        "tests": [
            {"input": "[1,3,5,7,9], 5", "expected": "2"},
            {"input": "[1,3,5,7,9], 1", "expected": "0"},
            {"input": "[1,3,5,7,9], 10", "expected": "-1"},
        ],
    },

    "task_hard": {
        "description": (
            "This authentication function has 3 security vulnerabilities:\n"
            "  Bug 1 (line 7): SQL injection - f-string directly in query.\n"
            "  Bug 2 (line 13): Timing attack - plain == leaks timing information.\n"
            "  Bug 3 (line 13): Plaintext password - no hashing used.\n\n"
            "Workflow:\n"
            "1. Send one 'comment' per bug - include line_number, severity, and comment_text.\n"
            "2. Send a 'fix' action - use parameterized queries, hmac.compare_digest, and hashlib.\n"
            "3. Send a 'submit' action with final_summary.\n\n"
            "The fix must address ALL 3 vulnerabilities to score full marks."
        ),
        "files": [
            CodeFile(
                filename="auth.py",
                content="""\
import sqlite3


def authenticate_user(username, password, db_path="users.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"SELECT password FROM users WHERE username = '{username}'"
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    if result is None:
        return False
    return result[0] == password
""",
            )
        ],
        "bugs": [
            {
                "line": 7,
                "type": "sql_injection",
                "severity": "Critical",
                "description": "f-string in SQL query allows injection",
            },
            {
                "line": 13,
                "type": "timing_attack",
                "severity": "High",
                "description": "== leaks timing info, use hmac.compare_digest",
            },
            {
                "line": 13,
                "type": "plaintext_password",
                "severity": "High",
                "description": "passwords compared in plaintext, use hashing",
            },
        ],
        "tests": [],
    },
}