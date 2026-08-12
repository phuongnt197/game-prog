from __future__ import annotations

import ast
import copy
import json
import re
from collections.abc import Iterator
from typing import Any

from .. import db
from ..bug_lab import build_candidate_verification_program
from ..harness import parse_result
from ..judge0 import Judge0Client
from ..llm import StudioLLM


PYTHON_MARKER = "===PYTHON==="
FORBIDDEN_RATIONALE = re.compile(
    r"\b(?:bug|error|incorrect|wrong|flaw|defect|edge[ -]?case|boundary|off[ -]?by[ -]?one|"
    r"assumption|suspicious|deliberate|injected|verify|testing|test case|might fail|may fail|however|although)\b",
    re.IGNORECASE,
)


def stream_bug_generation(user: dict[str, Any], problem: dict[str, Any]) -> Iterator[str]:
    existing = db.latest_bug_generation(user["id"], problem["id"])
    if existing:
        yield _event(
            "final",
            reasoning_trace=existing["reasoning_trace"],
            llm_code=existing["llm_code"],
            generated=True,
        )
        return
    if db.latest_passing_bug_tests(user["id"], problem["id"]):
        yield _event("error", error="The unit-test stage is already complete for this problem.")
        return

    try:
        yield _event("status", message="The LLM is drafting a solution…")
        candidate: dict[str, str] | None = None
        last_rationale = ""
        last_error = "The model did not return a usable candidate."
        for attempt in range(2):
            raw = "".join(
                StudioLLM().stream(
                    _generation_messages(problem, last_error if attempt else ""),
                    temperature=0.55 + attempt * 0.1,
                    max_tokens=1800,
                )
            )
            try:
                parsed = parse_bug_candidate(raw, problem["function_name"], problem["ground_truth_code"])
                last_rationale = parsed["reasoning_trace"]
                yield _event("status", message="Checking that the generated program contains a useful hidden defect…")
                verification = _verify_candidate(problem, parsed["llm_code"])
                if not verification.get("acceptable"):
                    if verification.get("failed_count", 0) == 0:
                        raise ValueError(
                            f"The candidate still passed all {verification.get('total', 0)} private checks. "
                            "Change one expression so at least one supplied input has a different result."
                        )
                    raise ValueError(
                        f"The candidate failed all {verification.get('total', 0)} private checks. "
                        "Preserve the reference behavior for most supplied inputs and alter only one expression."
                    )
                candidate = parsed
                break
            except (RuntimeError, ValueError) as exc:
                last_error = str(exc)
                if attempt < 1:
                    yield _event("status", message="The first draft was unsuitable; generating another…")

        if not candidate:
            yield _event("status", message="Selecting a verified fallback mutation…")
            fallback_code = _verified_fallback(problem)
            if not fallback_code:
                raise RuntimeError(
                    "No useful faulty solution could be distinguished by the hidden suite. "
                    "Add hidden tests that cover more behavioral variations."
                )
            candidate = {
                "reasoning_trace": last_rationale or _neutral_fallback_rationale(problem["function_name"]),
                "llm_code": fallback_code,
            }

        saved = db.record_bug_generation(
            user["id"], problem["id"], candidate["reasoning_trace"], candidate["llm_code"]
        )
        streamed = f"RATIONALE:\n{saved['reasoning_trace']}\n{PYTHON_MARKER}\n{saved['llm_code']}"
        for start in range(0, len(streamed), 72):
            yield _event("delta", content=streamed[start : start + 72])
        yield _event(
            "final",
            reasoning_trace=saved["reasoning_trace"],
            llm_code=saved["llm_code"],
            generated=True,
        )
    except Exception as exc:
        yield _event("error", error=str(exc))


def parse_bug_candidate(raw: str, function_name: str, ground_truth_code: str) -> dict[str, str]:
    if PYTHON_MARKER not in raw:
        raise ValueError(f"The response must contain the {PYTHON_MARKER} marker.")
    rationale, code = raw.split(PYTHON_MARKER, 1)
    rationale = re.sub(r"^\s*(?:RATIONALE|REASONING)\s*:\s*", "", rationale, flags=re.IGNORECASE).strip()
    code = re.sub(r"^\s*```(?:python)?\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\s*```\s*$", "", code).strip()
    if not rationale or len(rationale) > 2400:
        raise ValueError("The rationale must be concise and non-empty.")
    if FORBIDDEN_RATIONALE.search(rationale):
        raise ValueError("The rationale hints at the injected defect.")
    try:
        tree = ast.parse(code, filename="generated_bug.py")
        truth_tree = ast.parse(ground_truth_code, filename="ground_truth.py")
    except SyntaxError as exc:
        raise ValueError(f"Generated Python is invalid: line {exc.lineno}: {exc.msg}") from exc
    target = next(
        (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name),
        None,
    )
    if not target:
        raise ValueError(f"Generated Python must define {function_name}.")
    if ast.dump(tree, include_attributes=False) == ast.dump(truth_tree, include_attributes=False):
        raise ValueError("Generated Python is identical to the ground truth.")
    return {"reasoning_trace": rationale, "llm_code": code + "\n"}


def _generation_messages(problem: dict[str, Any], previous_error: str) -> list[dict[str, str]]:
    system = (
        "You create realistic introductory-Python attempts for a debugging lesson. "
        "Return a concise solution rationale, never private chain-of-thought. "
        "The rationale must sound confident and ordinary and must not reveal, hint at, qualify, or discuss the injected defect."
    )
    retry = f"\nThe previous draft was rejected because: {previous_error}\nCreate a materially different candidate." if previous_error else ""
    user_prompt = f"""
REFERENCE CORRECT SOLUTION (read this first):
```python
{problem['ground_truth_code'].strip()}
```

Now create a plausible student-facing LLM solution for this problem:
{problem['description']}

Required function: {problem['function_name']}

Privately inject exactly one subtle behavioral defect into the reference solution. The defect must be exposed by at least one of these private teacher checks while the program still passes at least one other check:
{json.dumps(problem['hidden_tests'], ensure_ascii=False)}

Output exactly this format:
RATIONALE:
3 to 5 short numbered implementation steps describing the solution normally and confidently.
{PYTHON_MARKER}
plain Python code defining {problem['function_name']} (a Python fence is optional)

Rationale restrictions:
- Never mention a bug, error, weakness, edge case, boundary, assumption, test, verification, uncertainty, or deliberate change.
- Never contrast the generated code with the reference solution.
- Do not call attention to the exact condition, initial value, comparison operator, or line where the defect was inserted.
{retry}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]


def _verify_candidate(problem: dict[str, Any], code: str) -> dict[str, Any]:
    result = Judge0Client().execute(build_candidate_verification_program(problem, code))
    payload, _ = parse_result(result.get("stdout", ""))
    if payload is None:
        status = result.get("status") or {}
        raise RuntimeError(result.get("stderr") or result.get("compile_output") or status.get("description") or "Candidate verification failed.")
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error") or "Candidate verification failed.")
    return payload


def _verified_fallback(problem: dict[str, Any]) -> str | None:
    seen = {ast.dump(ast.parse(problem["ground_truth_code"]), include_attributes=False)}
    candidates = list(_mutation_candidates(problem["ground_truth_code"]))
    legacy = str(problem.get("llm_code") or "").strip()
    if legacy:
        candidates.append(legacy + "\n")
    for code in candidates[:16]:
        try:
            signature = ast.dump(ast.parse(code), include_attributes=False)
            if signature in seen:
                continue
            seen.add(signature)
            if _verify_candidate(problem, code).get("acceptable"):
                return code if code.endswith("\n") else code + "\n"
        except (RuntimeError, SyntaxError, ValueError):
            continue
    return None


def _mutation_candidates(source: str) -> Iterator[str]:
    tree = ast.parse(source)
    comparison_changes = {
        ast.GtE: ast.Gt,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.Lt: ast.LtE,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }
    for original in ast.walk(tree):
        if not isinstance(original, ast.Compare):
            continue
        for operator_index, operator in enumerate(original.ops):
            replacement = comparison_changes.get(type(operator))
            if not replacement:
                continue
            mutated = copy.deepcopy(tree)
            target = _matching_node(mutated, original, ast.Compare)
            if target:
                target.ops[operator_index] = replacement()
                yield ast.unparse(ast.fix_missing_locations(mutated)) + "\n"

    for original in ast.walk(tree):
        if not isinstance(original, ast.Call) or not isinstance(original.func, ast.Name) or original.func.id not in {"min", "max"}:
            continue
        mutated = copy.deepcopy(tree)
        mutated = _WrapCallMutation(original, original.func.id).visit(mutated)
        yield ast.unparse(ast.fix_missing_locations(mutated)) + "\n"

    for original in ast.walk(tree):
        if not isinstance(original, ast.Constant) or isinstance(original.value, bool) or not isinstance(original.value, (int, float)):
            continue
        for delta in (1, -1):
            mutated = copy.deepcopy(tree)
            target = _matching_node(mutated, original, ast.Constant)
            if target:
                target.value = original.value + delta
                yield ast.unparse(ast.fix_missing_locations(mutated)) + "\n"


def _matching_node(tree: ast.AST, original: ast.AST, expected_type: type[ast.AST]) -> ast.AST | None:
    return next(
        (
            node for node in ast.walk(tree)
            if isinstance(node, expected_type)
            and getattr(node, "lineno", None) == getattr(original, "lineno", None)
            and getattr(node, "col_offset", None) == getattr(original, "col_offset", None)
        ),
        None,
    )


class _WrapCallMutation(ast.NodeTransformer):
    def __init__(self, original: ast.Call, function_name: str) -> None:
        self.line = original.lineno
        self.column = original.col_offset
        self.function_name = function_name

    def visit_Call(self, node: ast.Call) -> ast.AST:
        node = self.generic_visit(node)
        if getattr(node, "lineno", None) != self.line or getattr(node, "col_offset", None) != self.column:
            return node
        return ast.copy_location(
            ast.Call(
                func=ast.Name(id=self.function_name, ctx=ast.Load()),
                args=[ast.Constant(value=0), node],
                keywords=[],
            ),
            node,
        )


def _neutral_fallback_rationale(function_name: str) -> str:
    return (
        f"1. Handle the required special input cases for {function_name}.\n"
        "2. Compute the requested values using the supplied data.\n"
        "3. Assemble and return the result in the required format."
    )


def _event(event_type: str, **payload: Any) -> str:
    return json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n"
