from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


@dataclass
class StudioLLM:
    base_url: str = OPENAI_BASE_URL
    model: str = OPENAI_MODEL
    api_key: str = OPENAI_API_KEY

    def complete(self, messages: list[dict[str, str]], temperature: float = 0.2, max_tokens: int = 2200) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"LLM returned no choices: {data}")
        message = choices[0].get("message") or {}
        content = message.get("content") or message.get("reasoning_content") or message.get("reasoning") or ""
        return str(content).strip()


def draft_from_spec(
    *,
    mode: str,
    spec: str,
    template_name: str,
    current_code: str,
    current_tests: str,
) -> dict[str, Any]:
    mode = mode or "code"
    system = (
        "You help AIP1 students learn introductory Python with responsible AI assistance. "
        "Keep code simple: variables, types, conditionals, functions, loops, lists, and dictionaries. "
        "The platform supplies UI and execution; the student supplies only Python plugin logic."
    )
    if mode == "tests":
        user = f"""
Create JSON tests for an AIP1 Studio project.

Template: {template_name}
Student specification:
{spec}

Current Python code:
{current_code}

Return only a JSON array. Each item must have:
- "name": short test name
- "actions": list of action strings to play
- "expect": object mapping paths such as "state.energy", "state.location", "score", "won", or "lost" to expected values

Use 5 focused tests. Do not include prose outside the JSON.
"""
        raw = StudioLLM().complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=1800,
        )
        return {"mode": mode, "content": _extract_json_array(raw), "raw": raw}

    if mode == "feedback":
        user = f"""
Review this AIP1 Studio project against the student's specification.

Specification:
{spec}

Python code:
{current_code}

Tests:
{current_tests}

Give concise, actionable feedback. Focus on missing rules, weak tests, edge cases, and whether the code is understandable for an introductory Python student.
"""
        raw = StudioLLM().complete(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.2,
            max_tokens=1400,
        )
        return {"mode": mode, "content": raw, "raw": raw}

    user = f"""
Draft Python plugin code for an AIP1 Studio project.

Template: {template_name}
Student specification:
{spec}

Starting code to revise:
{current_code}

Required interface:
- TITLE and DESCRIPTION constants
- starting_state()
- describe_location(state) or describe_state(state)
- available_actions(state)
- apply_action(state, action)
- has_won(state)
- has_lost(state)
- score(state)

Return only Python code. Do not use input(), files, network access, third-party packages, or advanced syntax. Keep the logic readable enough for a first Python course.
"""
    raw = StudioLLM().complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=2600,
    )
    return {"mode": mode, "content": _extract_code(raw), "raw": raw}


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip()


def _extract_json_array(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = (fenced.group(1) if fenced else text).strip()
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start >= 0 and end > start:
        candidate = candidate[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array of tests")
    return json.dumps(parsed, indent=2)
