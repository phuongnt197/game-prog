from __future__ import annotations

import ast
import json
from typing import Any

from .harness import RESULT_PREFIX


DEFAULT_HUMAN_CODE_PROBLEMS: list[dict[str, Any]] = [
    {
        "id": "copilot-display-name",
        "activity_type": "human",
        "title": "Formatting a Display Name",
        "difficulty": "Easy",
        "position": 1,
        "description": (
            "Implement format_name(first, last). Remove surrounding whitespace and title-case each non-empty name. "
            "Return 'Last, First' when both are present, the single formatted name when only one is present, "
            "and an empty string when both are empty."
        ),
        "function_name": "format_name",
        "reasoning_trace": "",
        "llm_code": "",
        "ground_truth_code": '''def format_name(first, last):
    first = first.strip().title()
    last = last.strip().title()
    if first and last:
        return f"{last}, {first}"
    return last or first
''',
        "hidden_tests": [
            {"name": "two names", "input": [" ada ", "lovelace"], "expected": "Lovelace, Ada"},
            {"name": "mixed case", "input": ["gRACE", "HOPPER"], "expected": "Hopper, Grace"},
            {"name": "first only", "input": ["alan", "   "], "expected": "Alan"},
            {"name": "last only", "input": ["", "turing"], "expected": "Turing"},
            {"name": "both empty", "input": [" ", ""], "expected": ""},
        ],
        "min_student_tests": 1,
        "active": True,
    },
    {
        "id": "copilot-compress-runs",
        "activity_type": "human",
        "title": "Compressing Consecutive Values",
        "difficulty": "Medium",
        "position": 2,
        "description": (
            "Implement compress_runs(values). Return a new list containing [value, count] for each consecutive "
            "run. Equal values separated by another value belong to different runs. Do not mutate the input."
        ),
        "function_name": "compress_runs",
        "reasoning_trace": "",
        "llm_code": "",
        "ground_truth_code": '''def compress_runs(values):
    if not values:
        return []
    result = []
    current = values[0]
    count = 1
    for value in values[1:]:
        if value == current:
            count += 1
        else:
            result.append([current, count])
            current = value
            count = 1
    result.append([current, count])
    return result
''',
        "hidden_tests": [
            {"name": "empty", "input": [[]], "expected": []},
            {"name": "single", "input": [[4]], "expected": [[4, 1]]},
            {"name": "mixed runs", "input": [[1, 1, 2, 2, 2, 1]], "expected": [[1, 2], [2, 3], [1, 1]]},
            {"name": "no repeats", "input": [[1, 2, 3]], "expected": [[1, 1], [2, 1], [3, 1]]},
            {"name": "strings", "input": [["a", "a", "b"]], "expected": [["a", 2], ["b", 1]]},
        ],
        "min_student_tests": 1,
        "active": True,
    },
    {
        "id": "copilot-increasing-run",
        "activity_type": "human",
        "title": "Finding the Longest Increasing Run",
        "difficulty": "Hard",
        "position": 3,
        "description": (
            "Implement longest_increasing_run(values). Return a new list containing the longest contiguous run "
            "whose values are strictly increasing. Equal values break a run. If multiple runs have the same "
            "maximum length, return the earliest one. Return [] for an empty input and do not mutate the input."
        ),
        "function_name": "longest_increasing_run",
        "reasoning_trace": "",
        "llm_code": "",
        "ground_truth_code": '''def longest_increasing_run(values):
    if not values:
        return []
    best_start = 0
    best_length = 1
    current_start = 0
    for index in range(1, len(values)):
        if values[index] <= values[index - 1]:
            current_start = index
        current_length = index - current_start + 1
        if current_length > best_length:
            best_start = current_start
            best_length = current_length
    return values[best_start:best_start + best_length]
''',
        "hidden_tests": [
            {"name": "empty", "input": [[]], "expected": []},
            {"name": "single", "input": [[7]], "expected": [7]},
            {"name": "fully increasing", "input": [[1, 2, 4, 9]], "expected": [1, 2, 4, 9]},
            {"name": "several runs", "input": [[5, 1, 2, 3, 0, 4]], "expected": [1, 2, 3]},
            {"name": "earliest tie", "input": [[1, 3, 0, 2]], "expected": [1, 3]},
            {"name": "equal breaks", "input": [[1, 2, 2, 3, 4]], "expected": [2, 3, 4]},
            {"name": "negative values", "input": [[-3, -2, -1, -5]], "expected": [-3, -2, -1]},
        ],
        "min_student_tests": 1,
        "active": True,
    },
]


def analyze_solution(source: str, function_name: str) -> dict[str, Any]:
    source = str(source or "")
    if len(source) > 80_000:
        raise ValueError("solution code must be at most 80,000 characters")
    try:
        tree = ast.parse(source, filename="student_solution.py")
    except SyntaxError as exc:
        return {"valid": False, "error": f"Line {exc.lineno}: {exc.msg}"}
    function = next(
        (
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name
        ),
        None,
    )
    if not function:
        return {"valid": False, "error": f"Define the required function {function_name}(...)."}
    return {"valid": True, "error": ""}


def build_visible_test_program(
    solution_code: str,
    function_name: str,
    test_code: str,
    test_names: list[str],
) -> str:
    config = {
        "solution_code": solution_code,
        "function_name": function_name,
        "test_code": test_code,
        "test_names": test_names,
    }
    return f'''# AIP1 student-visible AI test harness
import base64 as _base64
import json as _json
import traceback as _traceback

_CONFIG = _json.loads({json.dumps(json.dumps(config))})
_PREFIX = {json.dumps(RESULT_PREFIX)}

def _run_test(solution_function, test_name):
    namespace = {{"__name__": "__visible_tests__", _CONFIG["function_name"]: solution_function}}
    try:
        exec(_CONFIG["test_code"], namespace)
        test_function = namespace.get(test_name)
        if not callable(test_function):
            raise AssertionError(test_name + " was not defined")
        test_function()
        return {{"name": test_name, "passed": True, "message": "Passed"}}
    except Exception as error:
        return {{
            "name": test_name,
            "passed": False,
            "message": type(error).__name__ + (": " + str(error) if str(error) else ""),
        }}

def _run():
    solution_namespace = {{"__name__": "__student_solution__"}}
    exec(_CONFIG["solution_code"], solution_namespace)
    solution_function = solution_namespace.get(_CONFIG["function_name"])
    if not callable(solution_function):
        raise ValueError("Solution must define " + _CONFIG["function_name"])
    checks = [_run_test(solution_function, name) for name in _CONFIG["test_names"]]
    return {{
        "ok": True,
        "passed": bool(checks) and all(item["passed"] for item in checks),
        "summary": {{"passed": sum(1 for item in checks if item["passed"]), "total": len(checks)}},
        "checks": checks,
    }}

try:
    _payload = _run()
except Exception:
    _payload = {{"ok": False, "passed": False, "error": _traceback.format_exc(), "checks": []}}
_encoded = _base64.b64encode(_json.dumps(_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(_PREFIX + _encoded)
'''
