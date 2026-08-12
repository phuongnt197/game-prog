from __future__ import annotations

from typing import Any

from .. import db
from ..assignments import assignment_cases, build_agent_program, get_assignment
from ..bug_lab import analyze_student_tests, build_bug_evaluation_program
from ..harness import parse_result
from ..judge0 import Judge0Client


def run_assignment(user: dict[str, Any], assignment_id: str, code: str, *, case_index: int = 0, run_all: bool = False) -> dict[str, Any]:
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise ValueError("Assignment not found")
    if not db.is_assignment_unlocked(user, assignment_id):
        raise PermissionError("Assignment is locked")
    cases = assignment_cases(assignment, include_hidden=run_all)
    if not cases:
        raise ValueError("Assignment has no test cases")
    selected = cases if run_all else [next((case for case in cases if case["index"] == case_index), cases[0])]
    client = Judge0Client()
    payloads = [_run_assignment_case(client, assignment, code, case) for case in selected]
    if not run_all:
        payload = payloads[0]
        payload.update({"assignment_id": assignment_id, "case_index": selected[0]["index"], "case_results": [_case_summary(selected[0], payload)]})
        return payload
    passed = all(item.get("passed") for item in payloads)
    display_index = next((index for index, item in enumerate(payloads) if not item.get("passed")), 0)
    display = payloads[display_index]
    results = [_case_summary(case, payload) for case, payload in zip(selected, payloads)]
    return {
        "ok": all(item.get("ok") for item in payloads), "passed": passed, "assignment_id": assignment_id,
        "case_index": selected[display_index]["index"], "case_name": selected[display_index]["name"],
        "summary": {"passed": sum(1 for item in payloads if item.get("passed")), "total": len(payloads)},
        "checks": results, "case_results": results, "world": display.get("world"), "trace": display.get("trace", []),
        "stdout": "\n".join(item.get("stdout", "") for item in payloads if item.get("stdout")), "error": display.get("error", ""),
    }


def _run_assignment_case(client: Judge0Client, assignment: dict, code: str, case: dict) -> dict:
    program = build_agent_program(code, assignment, world=case["world"], objectives=case["objectives"], case_name=case["name"])
    result = client.execute(program)
    payload, stdout = parse_result(result.get("stdout", ""))
    if not result.get("ok") and payload is None:
        payload = execution_error(result)
    elif payload is None:
        payload = {"ok": False, "passed": False, "error": "No AIP1 harness result was produced."}
    if stdout:
        payload["stdout"] = "\n".join(item for item in [payload.get("stdout", ""), stdout] if item)
    payload.update({"case_name": case["name"], "case_index": case["index"]})
    return payload


def run_bug_lab(user: dict, problem_id: str, body: dict[str, Any], stage: str) -> dict[str, Any]:
    problem = db.get_activity_problem(problem_id, "bug", include_secret=True)
    if not problem or not problem["active"]:
        raise ValueError("Bug-detection problem not found")
    saved_test_code = db.latest_passing_bug_tests(user["id"], problem_id)
    generation = db.latest_bug_generation(user["id"], problem_id)
    if generation:
        problem = {
            **problem,
            "reasoning_trace": generation["reasoning_trace"],
            "llm_code": generation["llm_code"],
        }
    elif not saved_test_code:
        raise PermissionError("Generate the LLM solution before writing unit tests.")
    if stage == "fix":
        test_code = saved_test_code
        if not test_code:
            raise PermissionError("Pass the unit-test stage before submitting a correction.")
    else:
        test_code = str(body.get("test_code") or "")
    corrected = str(body.get("corrected_code") or "") if stage == "fix" else None
    if stage == "fix" and not corrected.strip():
        raise ValueError("corrected code is required")
    analysis = analyze_student_tests(test_code, problem["function_name"], int(problem["min_student_tests"]))
    runtime_requirements = ("calls_function", "has_assertions", "zero_parameters", "safe_binding", "unique_names")
    runtime_ready = bool(analysis["test_names"]) and all(analysis["requirements"].get(name, False) for name in runtime_requirements)
    if not runtime_ready:
        requirements = {**analysis["requirements"], "unique_inputs": False, "valid": False, "detects_bug": False}
        payload = {
            "ok": True, "gate_passed": False, "passed": False, "requirements": requirements,
            "summary": {**analysis["summary"], "unique_count": 0, "valid_count": 0, "detected_count": 0},
            "checks": analysis["checks"], "correction_checks": [],
        }
    else:
        result = Judge0Client().execute(build_bug_evaluation_program(problem, test_code, analysis["test_names"], corrected))
        payload = _parsed_execution(result, "No bug-lab result was produced.")
        payload["requirements"] = {**analysis["requirements"], **payload.get("requirements", {})}
    db.record_bug_submission(user["id"], problem_id, stage, test_code, corrected or "", payload)
    return payload


def _parsed_execution(result: dict, missing_message: str = "No AIP1 harness result was produced.") -> dict:
    payload, stdout = parse_result(result.get("stdout", ""))
    if not result.get("ok") and payload is None:
        payload = execution_error(result)
    elif payload is None:
        payload = {"ok": False, "passed": False, "error": missing_message}
    if stdout:
        payload["stdout"] = stdout
    return payload


def execution_error(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status") or {}
    details = "\n".join(item for item in [f"Judge0 status: {status.get('description', 'Unknown')}", result.get("compile_output", ""), result.get("stderr", ""), result.get("message", "")] if item)
    return {"ok": False, "passed": False, "error": details or "Execution failed", "stdout": result.get("stdout", "")}


def _case_summary(case: dict, payload: dict) -> dict:
    summary = payload.get("summary") or {}
    details = f"{summary.get('passed', 0)}/{summary.get('total', 0)} checks passed" if summary else payload.get("error") or ("passed" if payload.get("passed") else "failed")
    return {"name": case["name"], "passed": bool(payload.get("passed")), "details": details}
