from __future__ import annotations

import ast
import json
from typing import Any

from .harness import RESULT_PREFIX


DEFAULT_BUG_PROBLEMS: list[dict[str, Any]] = [
    {
        "id": "shipping-boundary",
        "title": "Free Shipping at the Boundary",
        "difficulty": "Easy",
        "position": 1,
        "description": (
            "Implement shipping_cost(weight). Shipping costs $5 plus $2 per kilogram, "
            "but orders weighing 20 kg or more ship for free. Weight is a non-negative number."
        ),
        "function_name": "shipping_cost",
        "reasoning_trace": (
            "1. Use a guard clause for heavy orders that qualify for free shipping.\n"
            "2. Otherwise add the $5 base fee to $2 multiplied by the weight.\n"
            "3. Return the computed numeric cost."
        ),
        "llm_code": """def shipping_cost(weight):
    if weight > 20:
        return 0
    return 5 + 2 * weight
""",
        "ground_truth_code": """def shipping_cost(weight):
    if weight >= 20:
        return 0
    return 5 + 2 * weight
""",
        "hidden_tests": [
            {"name": "zero weight", "input": [0], "expected": 5},
            {"name": "light parcel", "input": [1], "expected": 7},
            {"name": "regular parcel", "input": [5], "expected": 15},
            {"name": "just below threshold", "input": [19], "expected": 43},
            {"name": "exact threshold", "input": [20], "expected": 0},
            {"name": "just above threshold", "input": [21], "expected": 0},
            {"name": "well above threshold", "input": [25], "expected": 0},
        ],
        "min_student_tests": 10,
        "active": True,
    },
    {
        "id": "negative-score-summary",
        "title": "Summarizing Negative Scores",
        "difficulty": "Medium",
        "position": 2,
        "description": (
            "Implement summarize_scores(scores). Return a dictionary with min, max, and average "
            "rounded to two decimals. Return None for an empty list. Scores may be negative."
        ),
        "function_name": "summarize_scores",
        "reasoning_trace": (
            "1. Return None when no scores are available.\n"
            "2. Walk through the scores while tracking the minimum, maximum, and total.\n"
            "3. Divide the total by the number of scores and round the average."
        ),
        "llm_code": """def summarize_scores(scores):
    if not scores:
        return None
    lowest = scores[0]
    highest = 0
    total = 0
    for score in scores:
        lowest = min(lowest, score)
        highest = max(highest, score)
        total += score
    return {"min": lowest, "max": highest, "average": round(total / len(scores), 2)}
""",
        "ground_truth_code": """def summarize_scores(scores):
    if not scores:
        return None
    return {
        "min": min(scores),
        "max": max(scores),
        "average": round(sum(scores) / len(scores), 2),
    }
""",
        "hidden_tests": [
            {"name": "empty", "input": [[]], "expected": None},
            {"name": "positive scores", "input": [[4, 8, 6]], "expected": {"min": 4, "max": 8, "average": 6.0}},
            {"name": "mixed scores", "input": [[-2, 0, 5]], "expected": {"min": -2, "max": 5, "average": 1.0}},
            {"name": "all negative", "input": [[-8, -2, -5]], "expected": {"min": -8, "max": -2, "average": -5.0}},
            {"name": "single negative", "input": [[-3]], "expected": {"min": -3, "max": -3, "average": -3.0}},
        ],
        "min_student_tests": 10,
        "active": True,
    },
    {
        "id": "touching-intervals",
        "title": "Merging Touching Intervals",
        "difficulty": "Hard",
        "position": 3,
        "description": (
            "Implement merge_intervals(intervals). Sort and merge overlapping or touching closed intervals. "
            "For example, [1, 3] and [3, 5] must become [1, 5]. Return a new list and do not mutate the input."
        ),
        "function_name": "merge_intervals",
        "reasoning_trace": (
            "1. Sort copies of the intervals by their starting point.\n"
            "2. Compare each interval with the last interval in the merged output.\n"
            "3. Extend the last interval on overlap; otherwise append a new interval."
        ),
        "llm_code": """def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted([list(interval) for interval in intervals])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        if start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
""",
        "ground_truth_code": """def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted([list(interval) for interval in intervals])
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
""",
        "hidden_tests": [
            {"name": "empty", "input": [[]], "expected": []},
            {"name": "overlapping", "input": [[[1, 4], [2, 6]]], "expected": [[1, 6]]},
            {"name": "separate", "input": [[[1, 2], [5, 7]]], "expected": [[1, 2], [5, 7]]},
            {"name": "touching", "input": [[[1, 3], [3, 5]]], "expected": [[1, 5]]},
            {"name": "touching chain", "input": [[[1, 2], [2, 3], [3, 4]]], "expected": [[1, 4]]},
            {"name": "nested and unsorted", "input": [[[5, 8], [1, 10], [2, 3]]], "expected": [[1, 10]]},
        ],
        "min_student_tests": 10,
        "active": True,
    },
]


def analyze_student_tests(source: str, function_name: str, minimum: int) -> dict[str, Any]:
    source = str(source or "")
    if len(source) > 80_000:
        raise ValueError("test source must be at most 80,000 characters")
    try:
        tree = ast.parse(source, filename="student_tests.py")
    except SyntaxError as exc:
        return {
            "passed": False,
            "test_names": [],
            "checks": [{"name": "Python syntax", "valid": False, "message": f"Line {exc.lineno}: {exc.msg}"}],
            "requirements": {"count": False, "calls_function": False, "has_assertions": False, "zero_parameters": False, "safe_binding": False},
            "summary": {"test_count": 0, "minimum": minimum},
        }

    test_nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
    names = [node.name for node in test_nodes]
    protected_binding = any(
        (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == function_name)
        or (isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id == function_name)
        for node in ast.walk(tree)
    )
    checks = []
    calls_ok = True
    assertions_ok = True
    parameters_ok = True
    for node in test_nodes:
        direct_calls = sum(
            1 for item in ast.walk(node)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == function_name
        )
        assertions = sum(1 for item in ast.walk(node) if isinstance(item, ast.Assert))
        parameter_count = len(node.args.posonlyargs) + len(node.args.args) + len(node.args.kwonlyargs)
        has_parameters = parameter_count > 0 or node.args.vararg is not None or node.args.kwarg is not None
        valid = direct_calls > 0 and assertions > 0 and not has_parameters
        calls_ok = calls_ok and direct_calls > 0
        assertions_ok = assertions_ok and assertions > 0
        parameters_ok = parameters_ok and not has_parameters
        missing = []
        if direct_calls == 0:
            missing.append(f"call {function_name}(...)")
        if assertions == 0:
            missing.append("at least one assert")
        if has_parameters:
            missing.append("a zero-parameter test function")
        checks.append({
            "name": node.name,
            "valid": valid,
            "message": "Static structure is valid" if valid else "Required: " + ", ".join(missing),
            "call_count": direct_calls,
            "assertion_count": assertions,
        })

    requirements = {
        "count": len(test_nodes) >= minimum,
        "calls_function": bool(test_nodes) and calls_ok,
        "has_assertions": bool(test_nodes) and assertions_ok,
        "zero_parameters": bool(test_nodes) and parameters_ok,
        "safe_binding": not protected_binding,
        "unique_names": len(names) == len(set(names)),
    }
    if protected_binding:
        checks.append({"name": "Protected function binding", "valid": False, "message": f"Tests may call but not redefine or assign {function_name}."})
    return {
        "passed": all(requirements.values()),
        "test_names": names,
        "checks": checks,
        "requirements": requirements,
        "summary": {"test_count": len(test_nodes), "minimum": minimum},
    }


def build_bug_evaluation_program(
    problem: dict[str, Any],
    student_test_code: str,
    test_names: list[str],
    corrected_code: str | None = None,
) -> str:
    config = {
        "function_name": problem["function_name"],
        "ground_truth_code": problem["ground_truth_code"],
        "llm_code": problem["llm_code"],
        "corrected_code": corrected_code,
        "hidden_tests": json.loads(problem["hidden_tests"]) if isinstance(problem["hidden_tests"], str) else problem["hidden_tests"],
        "student_test_code": student_test_code,
        "test_names": test_names,
        "min_student_tests": int(problem["min_student_tests"]),
    }
    return f'''# AIP1 AI bug-detection harness
import base64 as _base64
import copy as _copy
import json as _json
import traceback as _traceback

_CONFIG = _json.loads({json.dumps(json.dumps(config))})
_PREFIX = {json.dumps(RESULT_PREFIX)}

def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {{str(key): _jsonable(item) for key, item in value.items()}}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return repr(value)

def _load(source, label):
    namespace = {{"__name__": "__" + label + "__"}}
    exec(source, namespace)
    function = namespace.get(_CONFIG["function_name"])
    if not callable(function):
        raise ValueError(label + " code must define " + _CONFIG["function_name"])
    return function

def _call(function, inputs):
    copied = _copy.deepcopy(inputs)
    if isinstance(copied, dict):
        return _jsonable(function(**copied))
    return _jsonable(function(*copied))

def _attempt(function, inputs):
    try:
        return {{"ok": True, "value": _call(function, inputs)}}
    except Exception as error:
        return {{"ok": False, "error": type(error).__name__ + ": " + str(error)}}

def _attempt_test(function, test_name):
    calls = []
    def tracked(*args, **kwargs):
        calls.append({{"args": _jsonable(args), "kwargs": _jsonable(kwargs)}})
        return function(*_copy.deepcopy(args), **_copy.deepcopy(kwargs))
    namespace = {{"__name__": "__student_tests__", _CONFIG["function_name"]: tracked}}
    try:
        exec(_CONFIG["student_test_code"], namespace)
        test_function = namespace.get(test_name)
        if not callable(test_function):
            raise AssertionError(test_name + " was not defined")
        test_function()
        return {{"ok": True, "calls": calls}}
    except Exception as error:
        return {{"ok": False, "calls": calls, "error": type(error).__name__ + (": " + str(error) if str(error) else "")}}

def _run():
    truth = _load(_CONFIG["ground_truth_code"], "ground_truth")
    generated = _load(_CONFIG["llm_code"], "generated")
    corrected = _load(_CONFIG["corrected_code"], "corrected") if _CONFIG["corrected_code"] is not None else None
    student_checks = []
    signatures = set()
    for test_name in _CONFIG["test_names"]:
        truth_result = _attempt_test(truth, test_name)
        generated_result = _attempt_test(generated, test_name)
        for call in truth_result.get("calls", []):
            signatures.add(_json.dumps(call, sort_keys=True))
        valid = truth_result["ok"] and bool(truth_result.get("calls"))
        detects = valid and not generated_result["ok"]
        student_checks.append({{
            "name": test_name,
            "valid": valid,
            "detects_bug": detects,
            "call_count": len(truth_result.get("calls", [])),
            "inputs": truth_result.get("calls", []),
            "message": ("Valid and detects the injected bug" if detects else ("Valid, but the generated code passes" if valid else "Fails against the ground-truth implementation: " + truth_result.get("error", "function was not called"))) + "; captured " + str(len(truth_result.get("calls", []))) + " function call(s)",
        }})
    count_ok = len(student_checks) >= _CONFIG["min_student_tests"]
    unique_ok = len(signatures) >= len(student_checks)
    valid_ok = bool(student_checks) and all(item["valid"] for item in student_checks)
    detection_ok = any(item["detects_bug"] for item in student_checks)
    gate_passed = count_ok and unique_ok and valid_ok and detection_ok

    correction_checks = []
    correction_passed = False
    if corrected is not None and gate_passed:
        for index, test in enumerate(_CONFIG["hidden_tests"]):
            corrected_result = _attempt(corrected, test["input"])
            passed = corrected_result["ok"] and corrected_result.get("value") == _jsonable(test["expected"])
            correction_checks.append({{
                "name": "Hidden test " + str(index + 1),
                "passed": passed,
                "actual": corrected_result,
            }})
        correction_passed = bool(correction_checks) and all(item["passed"] for item in correction_checks)
    return {{
        "ok": True,
        "gate_passed": gate_passed,
        "passed": gate_passed and corrected is not None and correction_passed,
        "summary": {{
            "test_count": len(student_checks),
            "unique_count": len(signatures),
            "valid_count": sum(1 for item in student_checks if item["valid"]),
            "detected_count": sum(1 for item in student_checks if item["detects_bug"]),
            "minimum": _CONFIG["min_student_tests"],
        }},
        "requirements": {{"count": count_ok, "unique_inputs": unique_ok, "valid": valid_ok, "detects_bug": detection_ok}},
        "checks": student_checks,
        "correction_checks": correction_checks,
    }}

try:
    _payload = _run()
except Exception:
    _payload = {{"ok": False, "passed": False, "error": _traceback.format_exc()}}
_encoded = _base64.b64encode(_json.dumps(_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(_PREFIX + _encoded)
'''


def build_candidate_verification_program(problem: dict[str, Any], candidate_code: str) -> str:
    config = {
        "function_name": problem["function_name"],
        "candidate_code": candidate_code,
        "hidden_tests": json.loads(problem["hidden_tests"]) if isinstance(problem["hidden_tests"], str) else problem["hidden_tests"],
    }
    return f'''# AIP1 generated-candidate verification harness
import base64 as _base64
import copy as _copy
import json as _json
import traceback as _traceback

_CONFIG = _json.loads({json.dumps(json.dumps(config))})
_PREFIX = {json.dumps(RESULT_PREFIX)}

def _call(function, inputs):
    copied = _copy.deepcopy(inputs)
    if isinstance(copied, dict):
        return function(**copied)
    return function(*copied)

def _run():
    namespace = {{"__name__": "__generated_candidate__"}}
    exec(_CONFIG["candidate_code"], namespace)
    function = namespace.get(_CONFIG["function_name"])
    if not callable(function):
        raise ValueError("Generated code must define " + _CONFIG["function_name"])
    checks = []
    for index, test in enumerate(_CONFIG["hidden_tests"]):
        try:
            actual = _call(function, test["input"])
            passed = actual == test["expected"]
            checks.append({{"index": index, "passed": passed}})
        except Exception as error:
            checks.append({{"index": index, "passed": False, "error": type(error).__name__}})
    passed_count = sum(1 for item in checks if item["passed"])
    failed_count = len(checks) - passed_count
    return {{
        "ok": True,
        "acceptable": failed_count > 0 and (passed_count > 0 or len(checks) == 1),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "total": len(checks),
    }}

try:
    _payload = _run()
except Exception:
    _payload = {{"ok": False, "acceptable": False, "error": _traceback.format_exc()}}
_encoded = _base64.b64encode(_json.dumps(_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
print(_PREFIX + _encoded)
'''
