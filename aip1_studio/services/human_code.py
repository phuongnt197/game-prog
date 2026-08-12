from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator
from typing import Any

from .. import db
from ..bug_lab import analyze_student_tests, build_candidate_verification_program
from ..harness import parse_result
from ..human_code import analyze_solution, build_visible_test_program
from ..judge0 import Judge0Client
from ..llm import StudioLLM


TEST_MARKER = "===TESTS==="


def run_visible_tests(user: dict[str, Any], problem_id: str, body: dict[str, Any]) -> dict[str, Any]:
    problem = _problem(problem_id)
    solution_code = str(body.get("solution_code") or "")
    test_code = str(body.get("test_code") or "")
    solution_analysis = analyze_solution(solution_code, problem["function_name"])
    if not solution_analysis["valid"]:
        return {"ok": True, "passed": False, "error": solution_analysis["error"], "checks": []}
    test_analysis = analyze_student_tests(test_code, problem["function_name"], 1)
    if not test_analysis["passed"]:
        return {
            "ok": True,
            "passed": False,
            "error": "Visible tests must be zero-parameter test_* functions that call the assigned function and assert a result.",
            "checks": test_analysis["checks"],
            "requirements": test_analysis["requirements"],
        }
    result = Judge0Client().execute(
        build_visible_test_program(solution_code, problem["function_name"], test_code, test_analysis["test_names"])
    )
    payload = _execution_payload(result, "Visible tests did not produce a result.")
    return payload


def submit_solution(user: dict[str, Any], problem_id: str, body: dict[str, Any]) -> dict[str, Any]:
    problem = _problem(problem_id)
    solution_code = str(body.get("solution_code") or "")
    analysis = analyze_solution(solution_code, problem["function_name"])
    if not analysis["valid"]:
        payload = {
            "ok": True,
            "passed": False,
            "message": analysis["error"],
            "report": {
                "suite": "hidden",
                "passed_count": 0,
                "failed_count": 0,
                "total": 0,
                "not_run": True,
                "details_hidden": True,
            },
        }
    else:
        result = Judge0Client().execute(build_candidate_verification_program(problem, solution_code))
        private_payload = _execution_payload(result, "Hidden grading did not produce a result.")
        passed = bool(
            private_payload.get("ok")
            and private_payload.get("total", 0) > 0
            and private_payload.get("failed_count") == 0
        )
        payload = {
            "ok": bool(private_payload.get("ok")),
            "passed": passed,
            "message": "Solution accepted." if passed else "The solution does not pass the hidden suite yet.",
            "report": {
                "suite": "hidden",
                "passed_count": int(private_payload.get("passed_count") or 0),
                "failed_count": int(private_payload.get("failed_count") or 0),
                "total": int(private_payload.get("total") or 0),
                "not_run": not bool(private_payload.get("ok")),
                "details_hidden": True,
            },
        }
        if private_payload.get("error") and not private_payload.get("ok"):
            payload["error"] = "The solution could not be executed. Check its syntax and required function."
        db.record_human_code_submission(user["id"], problem_id, solution_code, passed, private_payload)
    return payload


def stream_copilot(
    problem: dict[str, Any],
    message: str,
    solution_code: str,
    test_code: str,
    history: list[dict[str, Any]],
) -> Iterator[str]:
    message = message.strip()
    if not message:
        yield _event("error", error="Enter a question for the AI copilot.")
        return
    try:
        yield _event("status", message="AI copilot is reviewing your work…")
        wants_tests = _requests_test_code(message)
        last_error = ""
        for attempt in range(2):
            live_response = _CopilotLiveResponse(problem["function_name"], solution_code)
            sent_delta = False
            sent_test_status = False
            try:
                model_stream = StudioLLM().stream(
                    _copilot_messages(problem, message, solution_code, test_code, history, last_error),
                    temperature=0.25,
                    max_tokens=1400,
                )
                for chunk in model_stream:
                    for guidance_chunk in live_response.feed(chunk):
                        sent_delta = True
                        yield _event("delta", content=guidance_chunk)
                    if live_response.in_tests and not sent_test_status:
                        sent_test_status = True
                        yield _event("status", message="Checking the AI-written tests…")
                for guidance_chunk in live_response.finish():
                    sent_delta = True
                    yield _event("delta", content=guidance_chunk)
                response = parse_copilot_response(
                    live_response.raw,
                    problem["function_name"],
                    require_tests=wants_tests,
                    student_code=solution_code,
                )
                yield _event("final", **response)
                return
            except ValueError as exc:
                last_error = str(exc)
                if sent_delta:
                    yield _event("reset")
                if attempt == 0:
                    yield _event("status", message="Refining the response into specific, actionable guidance…")
        response = {
            "guidance": _fallback_guidance(problem, solution_code),
            "test_code": "",
        }
        yield _event("delta", content=response["guidance"])
        yield _event("final", **response)
    except Exception as exc:
        yield _event("error", error=str(exc))


def parse_copilot_response(
    raw: str,
    function_name: str,
    *,
    require_tests: bool = False,
    student_code: str = "",
) -> dict[str, str]:
    if TEST_MARKER in raw:
        guidance, test_code = raw.split(TEST_MARKER, 1)
    else:
        guidance, test_code = raw, ""
    guidance = re.sub(r"^\s*GUIDANCE\s*:\s*", "", guidance, flags=re.IGNORECASE).strip()
    test_code = re.sub(r"^\s*```(?:python)?\s*", "", test_code, flags=re.IGNORECASE)
    test_code = re.sub(r"\s*```\s*$", "", test_code).strip()
    if not guidance:
        raise ValueError("The response must contain guidance.")
    _assert_guidance_safe(guidance, function_name, student_code)
    if test_code:
        analysis = analyze_student_tests(test_code, function_name, 1)
        if not analysis["passed"]:
            raise ValueError("The test section must contain only valid test_* functions for the assigned function.")
        tree = ast.parse(test_code)
        disallowed = [
            node for node in tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
        ]
        if disallowed or any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("test_")
            for node in tree.body
        ):
            raise ValueError("The test section may contain only test_* function definitions.")
        forbidden_inside_tests = (
            ast.FunctionDef, ast.AsyncFunctionDef, ast.For, ast.AsyncFor, ast.While, ast.If,
            ast.Lambda, ast.ClassDef, ast.Import, ast.ImportFrom, ast.BinOp,
        )
        if any(
            node is not function and isinstance(node, forbidden_inside_tests)
            for function in tree.body for node in ast.walk(function)
        ):
            raise ValueError("AI tests must use concrete inputs and expected constants, not reproduce solution logic.")
        if any(
            isinstance(node, ast.Call)
            and not (isinstance(node.func, ast.Name) and node.func.id == function_name)
            for function in tree.body for node in ast.walk(function)
        ):
            raise ValueError("AI tests may call only the assigned function.")
        test_code += "\n"
    elif require_tests:
        raise ValueError("The student requested tests, but the response did not include valid test code.")
    return {"guidance": guidance, "test_code": test_code}


class _CopilotLiveResponse:
    """Expose safe, complete guidance lines while retaining the full model response."""

    def __init__(self, function_name: str, student_code: str = "") -> None:
        self.function_name = function_name
        self.student_code = student_code
        self.raw = ""
        self.pending = ""
        self.guidance = ""
        self.started_guidance = False
        self.in_tests = False

    def feed(self, chunk: str) -> Iterator[str]:
        self.raw += chunk
        self.pending += chunk
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            streamed = self._accept_line(line.rstrip("\r"), "\n")
            if streamed:
                yield streamed

    def finish(self) -> Iterator[str]:
        if not self.pending:
            return
        line = self.pending
        self.pending = ""
        streamed = self._accept_line(line.rstrip("\r"), "")
        if streamed:
            yield streamed

    def _accept_line(self, line: str, ending: str) -> str:
        if self.in_tests:
            return ""
        if TEST_MARKER in line:
            line, _ = line.split(TEST_MARKER, 1)
            self.in_tests = True
            if not line:
                return ""

        if not self.started_guidance:
            if not line.strip():
                return ""
            prefix = re.match(r"^\s*GUIDANCE\s*:\s*", line, flags=re.IGNORECASE)
            if prefix:
                line = line[prefix.end():]
            self.started_guidance = True
            if not line:
                return ""

        if not line and not ending:
            return ""
        candidate = self.guidance + line + ending
        _assert_guidance_safe(candidate, self.function_name, self.student_code, allow_incomplete_fence=True)
        self.guidance = candidate
        return line + ending


def _assert_guidance_safe(
    guidance: str,
    function_name: str,
    student_code: str = "",
    *,
    allow_incomplete_fence: bool = False,
) -> None:
    """Allow concrete code review while blocking newly authored solution statements.

    The copilot may quote a line that is already in the live editor. New executable
    statements belong only in the validated test section, never in guidance.
    """
    student_lines = {
        _normalise_fragment(line)
        for line in student_code.splitlines()
        if line.strip()
    }

    assigned_definition = re.compile(rf"\b(?:async\s+)?def\s+{re.escape(function_name)}\s*\(")
    for block in re.findall(r"```(?:python)?\s*\n?(.*?)```", guidance, flags=re.IGNORECASE | re.DOTALL):
        block_lines = [line for line in block.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if any(not _is_student_fragment(line, student_lines) for line in block_lines):
            raise ValueError("The response attempted to provide replacement solution code.")

    if guidance.count("```") % 2 and not allow_incomplete_fence:
        raise ValueError("The guidance contained an incomplete Markdown code block.")

    for inline in re.findall(r"`([^`\n]+)`", guidance):
        if (assigned_definition.search(inline) or _looks_like_python_statement(inline)) and not _is_student_fragment(inline, student_lines):
            raise ValueError("The response attempted to provide a new solution code statement.")

    for raw_line in guidance.splitlines():
        if "```" in raw_line:
            continue
        line = raw_line.strip()
        if not line or line.startswith(("#", ">")):
            continue
        if assigned_definition.match(line) and not _is_student_fragment(line, student_lines):
            raise ValueError("The response attempted to provide assigned-function solution code.")
        if _looks_like_python_statement(line) and not _is_student_fragment(line, student_lines):
            raise ValueError("The response attempted to provide a new solution code statement.")


def _normalise_fragment(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _is_student_fragment(value: str, student_lines: set[str]) -> bool:
    fragment = _normalise_fragment(value.strip().strip("`"))
    if fragment in student_lines:
        return True
    return len(fragment) >= 6 and any(fragment in line for line in student_lines)


def _looks_like_python_statement(value: str) -> bool:
    line = value.strip()
    return bool(re.match(
        r"^(?:(?:async\s+)?def\s+\w+\s*\(|class\s+\w+\b|return\b|yield\b|raise\b|"
        r"(?:if|elif|for|while|with|match|case|except)\s+.+:|(?:else|try|finally):|"
        r"[A-Za-z_]\w*(?:\s*\[[^\n]+\]|(?:\.\w+)*)?\s*(?:=|\+=|-=|\*=|/=|//=|%=))",
        line,
    ))


def _fallback_guidance(problem: dict[str, Any], solution_code: str) -> str:
    """Return useful, non-solution feedback if model output repeatedly violates policy."""
    function_name = problem["function_name"]
    try:
        tree = ast.parse(solution_code)
    except SyntaxError as exc:
        location = f" near line {exc.lineno}" if exc.lineno else ""
        return (
            "## Review\n\n"
            f"Python cannot parse the current draft{location}: **{exc.msg}**. "
            "Fix that syntax issue first, then trace one ordinary input through the function.\n\n"
            "**Next step:** check the indicated line together with the line immediately before it for an unfinished "
            "expression, missing delimiter, or indentation mismatch."
        )

    assigned = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name),
        None,
    )
    if assigned is None:
        return (
            "## Review\n\n"
            f"The current draft does not define the required `{function_name}` function, so it cannot be tested yet.\n\n"
            "**Next step:** use the function signature shown in the starter and first write down the required output "
            "for one ordinary input and each boundary case from the problem statement."
        )
    if not assigned.body or all(isinstance(node, ast.Pass) for node in assigned.body):
        return (
            "## Review\n\n"
            "The required function is still a placeholder, so there is no behavior to review yet.\n\n"
            "**Next step:** identify the input categories described by the problem, decide the expected output for one "
            "example in each category, and implement the first category before asking for another review."
        )

    return_count = sum(isinstance(node, ast.Return) for node in ast.walk(assigned))
    branch_count = sum(isinstance(node, (ast.If, ast.For, ast.While)) for node in ast.walk(assigned))
    return (
        "## Review\n\n"
        f"Your current function has **{branch_count} decision or loop path(s)** and **{return_count} explicit return "
        "path(s)**. Trace an ordinary input and every boundary case from the public statement, and note the first "
        "place where the produced value or type differs from the contract.\n\n"
        "**Next step:** add one focused visible test for that case, run it, and use the first failing assertion to "
        "narrow the next change."
    )


def _requests_test_code(message: str) -> bool:
    """Require a test section only when the student asks for new tests, not when discussing tests."""
    text = " ".join(message.lower().split())
    action = r"(?:write|create|generate|add|give|produce|design|suggest)"
    return bool(
        re.search(rf"\b{action}\b[^.!?]{{0,60}}\b(?:unit\s+)?tests?\b", text)
        or re.search(rf"\b(?:unit\s+)?tests?\b[^.!?]{{0,40}}\b{action}\b", text)
    )


def _copilot_messages(
    problem: dict[str, Any],
    message: str,
    solution_code: str,
    test_code: str,
    history: list[dict[str, Any]],
    previous_error: str,
) -> list[dict[str, str]]:
    system = f"""
You are a practical Python learning copilot. The student must implement {problem['function_name']} independently.
You do not have and must not request the reference answer or hidden tests.

Your job is to move the student forward. Never answer an allowed request by merely restating the no-solution-code
policy or saying that you cannot help. Examine the live editor code closely and make the response specific to it.

For a code review:
- Identify the most important concrete issue visible in the student's current code.
- Quote short fragments that already exist in the live editor with inline Markdown when useful.
- Explain the consequence: which public edge-case category, control-flow path, output value, or output type is affected.
- Distinguish confirmed problems from questions or possible risks.
- State the relevant programming rule or algorithmic insight directly; do not hide every diagnosis behind questions.
- End with one actionable conceptual next step and a way for the student to verify it.

For a next-step request:
- Recommend one specific algorithmic or debugging direction in prose, explain why it matters, and suggest a check.
- You may discuss branches, loops, data structures, invariants, Python operations, and the student's existing lines.
- It is acceptable to explain the correct rule or invariant in prose when that is what helps the student progress.

For a test request:
- Write useful visible Python unit tests after {TEST_MARKER}.
- Test code must contain only zero-parameter test_* functions, call {problem['function_name']} with concrete inputs,
  and use assert with concrete expected values.
- Cover public requirements and boundaries without claiming that they came from hidden tests.

The teaching boundary:
- Do not write a new Python statement, replacement function, patch, or directly translatable pseudocode that
  implements {problem['function_name']} for the student.
- Do not provide a code block in guidance. Existing student fragments may be mentioned inline.
- Do not complete or rewrite the student's solution, even if directly asked. Instead, give the most specific
  diagnosis and conceptual next action that remains educationally appropriate.
- Do not claim access to the reference answer or hidden tests.

Return exactly:
GUIDANCE:
specific, concise guidance formatted as Markdown
{TEST_MARKER}
optional Python test_* functions only

Omit {TEST_MARKER} unless tests were requested or are clearly useful. Do not use raw HTML.
"""
    context = f"""
PUBLIC PROBLEM:
{problem['description']}

STUDENT'S CURRENT LIVE EDITOR SOLUTION (authoritative and possibly unsaved):
```python
{solution_code}
```

CURRENT LIVE VISIBLE TESTS (authoritative and possibly unsaved):
```python
{test_code}
```
"""
    messages = [{"role": "system", "content": system + "\n" + context}]
    for item in history[-8:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "")[:3000]
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    retry = f"\nYour previous response was rejected: {previous_error}. Follow the policy and format exactly." if previous_error else ""
    messages.append({"role": "user", "content": message + retry})
    return messages


def _problem(problem_id: str) -> dict[str, Any]:
    problem = db.get_activity_problem(problem_id, "human", include_secret=True)
    if not problem or not problem["active"]:
        raise ValueError("Programming problem not found")
    return problem


def _execution_payload(result: dict[str, Any], missing: str) -> dict[str, Any]:
    payload, stdout = parse_result(result.get("stdout", ""))
    if payload is None:
        status = result.get("status") or {}
        return {
            "ok": False,
            "passed": False,
            "error": result.get("stderr") or result.get("compile_output") or status.get("description") or missing,
            "checks": [],
        }
    if stdout:
        payload["stdout"] = stdout
    return payload


def _event(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"
