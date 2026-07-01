from __future__ import annotations

import base64
import json
from typing import Any


RESULT_PREFIX = "__AIP1_STUDIO_RESULT__"


def build_play_program(student_code: str, actions: list[str]) -> str:
    return f"""
{student_code}

# --- AIP1 Studio Judge0 harness ---
import base64 as _aip1_base64
import copy as _aip1_copy
import json as _aip1_json
import traceback as _aip1_traceback

_AIP1_ACTIONS = _aip1_json.loads({_py_json_string(actions)})
_AIP1_RESULT_PREFIX = {_json(RESULT_PREFIX)}


def _aip1_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {{str(key): _aip1_jsonable(item) for key, item in value.items()}}
    if isinstance(value, (list, tuple, set)):
        return [_aip1_jsonable(item) for item in value]
    return repr(value)


def _aip1_call_description(state):
    if "describe_location" in globals():
        return str(describe_location(state))
    if "describe_state" in globals():
        return str(describe_state(state))
    return _aip1_json.dumps(_aip1_jsonable(state), indent=2)


def _aip1_action_id(action):
    if isinstance(action, dict):
        return str(action.get("id") or action.get("name") or action.get("label") or action)
    return str(action)


def _aip1_normalize_actions(actions):
    normalized = []
    for action in actions or []:
        if isinstance(action, dict):
            action_id = _aip1_action_id(action)
            normalized.append({{
                "id": action_id,
                "label": str(action.get("label") or action_id),
                "description": str(action.get("description") or ""),
            }})
        else:
            normalized.append({{"id": str(action), "label": str(action), "description": ""}})
    return normalized


def _aip1_require_contract():
    required = ["starting_state", "available_actions", "apply_action", "has_won", "has_lost", "score"]
    missing = [name for name in required if name not in globals() or not callable(globals()[name])]
    if missing:
        raise ValueError("Missing required function(s): " + ", ".join(missing))


def _aip1_run_game():
    _aip1_require_contract()
    state = starting_state()
    trace = []
    for action in _AIP1_ACTIONS:
        choices = available_actions(state)
        valid_ids = [_aip1_action_id(item) for item in choices or []]
        if valid_ids and str(action) not in valid_ids:
            raise ValueError(f"Invalid action {{action!r}}. Available actions: {{valid_ids}}")
        before = _aip1_copy.deepcopy(state)
        updated = apply_action(state, str(action))
        if updated is not None:
            state = updated
        trace.append({{
            "action": str(action),
            "before": _aip1_jsonable(before),
            "after": _aip1_jsonable(state),
        }})

    won = bool(has_won(state))
    lost = bool(has_lost(state))
    actions = [] if won or lost else _aip1_normalize_actions(available_actions(state))
    return {{
        "ok": True,
        "title": str(globals().get("TITLE", "Untitled Project")),
        "description": str(globals().get("DESCRIPTION", "")),
        "kind": str(globals().get("PROJECT_KIND", "interactive")),
        "state": _aip1_jsonable(state),
        "state_text": _aip1_call_description(state),
        "actions": actions,
        "score": _aip1_jsonable(score(state)),
        "won": won,
        "lost": lost,
        "game_over": won or lost,
        "trace": trace,
    }}


try:
    _aip1_payload = _aip1_run_game()
except Exception:
    _aip1_payload = {{"ok": False, "error": _aip1_traceback.format_exc()}}

_aip1_encoded = _aip1_base64.b64encode(
    _aip1_json.dumps(_aip1_payload, ensure_ascii=False).encode("utf-8")
).decode("ascii")
print(_AIP1_RESULT_PREFIX + _aip1_encoded)
"""


def build_test_program(student_code: str, tests: list[dict[str, Any]]) -> str:
    return f"""
{student_code}

# --- AIP1 Studio Judge0 test harness ---
import base64 as _aip1_base64
import copy as _aip1_copy
import json as _aip1_json
import traceback as _aip1_traceback

_AIP1_TESTS = _aip1_json.loads({_py_json_string(tests)})
_AIP1_RESULT_PREFIX = {_json(RESULT_PREFIX)}


def _aip1_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {{str(key): _aip1_jsonable(item) for key, item in value.items()}}
    if isinstance(value, (list, tuple, set)):
        return [_aip1_jsonable(item) for item in value]
    return repr(value)


def _aip1_action_id(action):
    if isinstance(action, dict):
        return str(action.get("id") or action.get("name") or action.get("label") or action)
    return str(action)


def _aip1_normalize_actions(actions):
    return [_aip1_action_id(action) for action in (actions or [])]


def _aip1_get_path(snapshot, path):
    value = snapshot
    for part in path.split("."):
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, list):
            value = value[int(part)]
        else:
            value = getattr(value, part)
    return value


def _aip1_require_contract():
    required = ["starting_state", "available_actions", "apply_action", "has_won", "has_lost", "score"]
    missing = [name for name in required if name not in globals() or not callable(globals()[name])]
    if missing:
        raise AssertionError("Missing required function(s): " + ", ".join(missing))


def _aip1_play(actions):
    state = starting_state()
    for action in actions:
        available = _aip1_normalize_actions(available_actions(state))
        if available and str(action) not in available:
            raise AssertionError(f"Action {{action!r}} is not available. Available actions: {{available}}")
        updated = apply_action(state, str(action))
        if updated is not None:
            state = updated
    return state


def _aip1_snapshot(state):
    return {{
        "state": _aip1_jsonable(state),
        "score": _aip1_jsonable(score(state)),
        "won": bool(has_won(state)),
        "lost": bool(has_lost(state)),
        "actions": _aip1_normalize_actions(available_actions(state)),
    }}


def _aip1_contract_tests():
    results = []
    try:
        _aip1_require_contract()
        state = starting_state()
        assert isinstance(state, dict), "starting_state() must return a dictionary"
        actions = available_actions(state)
        assert isinstance(actions, list), "available_actions(state) must return a list"
        assert isinstance(bool(has_won(state)), bool)
        assert isinstance(bool(has_lost(state)), bool)
        score(state)
        if "describe_location" in globals():
            assert isinstance(describe_location(state), str), "describe_location(state) must return a string"
        if "describe_state" in globals():
            assert isinstance(describe_state(state), str), "describe_state(state) must return a string"
        if actions:
            trial_state = _aip1_copy.deepcopy(state)
            updated = apply_action(trial_state, _aip1_action_id(actions[0]))
            assert updated is None or isinstance(updated, dict), "apply_action must mutate state or return a dictionary"
        results.append({{"name": "Plugin contract", "passed": True, "details": "Required functions behave like the platform expects."}})
    except Exception as exc:
        results.append({{"name": "Plugin contract", "passed": False, "details": str(exc)}})
    return results


def _aip1_student_test(test):
    name = str(test.get("name") or "Unnamed test")
    actions = test.get("actions") or []
    expected = test.get("expect") or test.get("expects") or {{}}
    state = _aip1_play(actions)
    snapshot = _aip1_snapshot(state)
    failures = []
    for path, want in expected.items():
        try:
            got = _aip1_get_path(snapshot, str(path))
            if got != want:
                failures.append(f"{{path}} expected {{want!r}} but got {{got!r}}")
        except Exception as exc:
            failures.append(f"{{path}} could not be read: {{exc}}")
    return {{
        "name": name,
        "passed": len(failures) == 0,
        "details": "ok" if not failures else "; ".join(failures),
        "snapshot": snapshot,
    }}


def _aip1_run_tests():
    results = _aip1_contract_tests()
    for test in _AIP1_TESTS:
        try:
            results.append(_aip1_student_test(test))
        except Exception:
            results.append({{
                "name": str(test.get("name") or "Unnamed test"),
                "passed": False,
                "details": _aip1_traceback.format_exc(),
            }})
    passed = sum(1 for item in results if item.get("passed"))
    return {{
        "ok": True,
        "summary": {{"passed": passed, "total": len(results)}},
        "results": results,
    }}


try:
    _aip1_payload = _aip1_run_tests()
except Exception:
    _aip1_payload = {{"ok": False, "error": _aip1_traceback.format_exc()}}

_aip1_encoded = _aip1_base64.b64encode(
    _aip1_json.dumps(_aip1_payload, ensure_ascii=False).encode("utf-8")
).decode("ascii")
print(_AIP1_RESULT_PREFIX + _aip1_encoded)
"""


def parse_result(stdout: str) -> tuple[dict[str, Any] | None, str]:
    visible_lines: list[str] = []
    payload: dict[str, Any] | None = None
    for line in stdout.splitlines():
        if line.startswith(RESULT_PREFIX):
            encoded = line[len(RESULT_PREFIX) :]
            payload = json.loads(base64.b64decode(encoded).decode("utf-8"))
        else:
            visible_lines.append(line)
    return payload, "\n".join(visible_lines).strip()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _py_json_string(value: Any) -> str:
    return repr(json.dumps(value, ensure_ascii=False))
