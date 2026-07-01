from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from . import db
from .assignments import ASSIGNMENTS, assignment_cases, build_agent_program, get_assignment, public_assignment
from .config import (
    JUDGE0_HOST,
    JUDGE0_PORT,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    PACMAN_DIR,
    SERVER_HOST,
    SERVER_PORT,
    STATIC_DIR,
)
from .harness import build_play_program, build_test_program, parse_result
from .judge0 import Judge0Client
from .llm import draft_from_spec
from .templates import get_template, template_list


SESSION_COOKIE = "aip1_session"


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "AIP1Studio/0.2"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                self._send_static(STATIC_DIR / "index.html")
            elif path.startswith("/static/"):
                self._send_static(STATIC_DIR / unquote(path.removeprefix("/static/")))
            elif path == "/pacman":
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/pacman/")
                self.end_headers()
            elif path == "/pacman/":
                self._current_user()
                self._send_static(PACMAN_DIR / "index.html", PACMAN_DIR)
            elif path.startswith("/pacman/"):
                self._current_user()
                self._send_static(PACMAN_DIR / unquote(path.removeprefix("/pacman/")), PACMAN_DIR)
            elif path == "/api/health":
                self._send_json(
                    {
                        "ok": True,
                        "judge0": f"{JUDGE0_HOST}:{JUDGE0_PORT}",
                        "openai_base_url": OPENAI_BASE_URL,
                        "openai_model": OPENAI_MODEL,
                    }
                )
            elif path == "/api/me":
                user = self._current_user(required=False)
                self._send_json({"user": db.public_user(user) if user else None})
            elif path == "/api/assignments":
                user = self._current_user()
                completed = db.completed_assignment_ids(user["id"])
                drafts = db.assignment_drafts(user["id"])
                assignments = []
                for assignment in ASSIGNMENTS:
                    unlocked = db.is_assignment_unlocked(user, assignment["id"])
                    item = public_assignment(assignment, unlocked, assignment["id"] in completed)
                    if unlocked and assignment["id"] in drafts:
                        item["draft_code"] = drafts[assignment["id"]]["code"]
                        item["draft_updated_at"] = drafts[assignment["id"]]["updated_at"]
                    assignments.append(item)
                self._send_json({"assignments": assignments})
            elif path.startswith("/api/assignments/"):
                user = self._current_user()
                assignment_id = unquote(path.removeprefix("/api/assignments/"))
                assignment = get_assignment(assignment_id)
                if not assignment:
                    self._send_error(HTTPStatus.NOT_FOUND, "Assignment not found")
                    return
                unlocked = db.is_assignment_unlocked(user, assignment_id)
                if not unlocked:
                    self._send_error(HTTPStatus.FORBIDDEN, "Assignment is locked")
                    return
                completed = assignment_id in db.completed_assignment_ids(user["id"])
                item = public_assignment(assignment, True, completed)
                draft = db.assignment_draft(user["id"], assignment_id)
                if draft:
                    item["draft_code"] = draft["code"]
                    item["draft_updated_at"] = draft["updated_at"]
                self._send_json(item)
            elif path == "/api/templates":
                self._require_studio()
                self._send_json({"templates": template_list()})
            elif path.startswith("/api/templates/"):
                self._require_studio()
                template_id = unquote(path.removeprefix("/api/templates/"))
                self._send_json(get_template(template_id))
            elif path == "/api/projects":
                self._current_user()
                self._send_json({"projects": db.list_projects()})
            elif path.startswith("/api/projects/"):
                self._current_user()
                slug = unquote(path.removeprefix("/api/projects/"))
                project = db.get_project(slug)
                if not project:
                    self._send_error(HTTPStatus.NOT_FOUND, "Project not found")
                else:
                    self._send_json(project)
            elif path == "/api/admin/overview":
                self._require_admin()
                self._send_json(db.admin_overview())
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
        except PermissionError as exc:
            self._send_error(HTTPStatus.FORBIDDEN, str(exc))
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
            if path == "/api/auth/login":
                self._login(body)
            elif path == "/api/auth/logout":
                self._logout()
            elif path == "/api/auth/register":
                user = db.create_user(
                    username=str(body.get("username") or ""),
                    password=str(body.get("password") or ""),
                    display_name=str(body.get("display_name") or body.get("username") or ""),
                    role="student",
                    must_change_password=False,
                )
                token = db.create_session(user["id"])
                self._send_json({"user": db.public_user(user)}, headers=[_session_cookie(token)])
            elif path == "/api/auth/change-password":
                user = self._current_user()
                db.change_password(user["id"], str(body.get("old_password") or ""), str(body.get("new_password") or ""))
                user = db.get_user_by_id(user["id"])
                self._send_json({"user": db.public_user(user)})
            elif path == "/api/behavior/log":
                user = self._current_user()
                events = body.get("events") or []
                if not isinstance(events, list):
                    raise ValueError("events must be a list")
                db.log_events(user["id"], events)
                self._send_json({"ok": True})
            elif path.startswith("/api/assignments/") and path.endswith("/draft"):
                user = self._current_user()
                assignment_id = unquote(path[len("/api/assignments/") : -len("/draft")])
                assignment = get_assignment(assignment_id)
                if not assignment or assignment.get("is_project"):
                    raise ValueError("Assignment not found")
                if not db.is_assignment_unlocked(user, assignment_id):
                    raise PermissionError("Assignment is locked")
                draft = db.save_assignment_draft(user["id"], assignment_id, str(body.get("code") or ""))
                self._send_json({"ok": True, "assignment_id": assignment_id, "updated_at": draft["updated_at"]})
            elif path.startswith("/api/assignments/") and path.endswith("/run"):
                user = self._current_user()
                assignment_id = unquote(path[len("/api/assignments/") : -len("/run")])
                code = str(body.get("code") or "")
                case_index = int(body.get("case_index") or 0)
                db.save_assignment_draft(user["id"], assignment_id, code)
                self._send_json(self._run_assignment(user, assignment_id, code, case_index=case_index, run_all_cases=False))
            elif path.startswith("/api/assignments/") and path.endswith("/submit"):
                user = self._current_user()
                assignment_id = unquote(path[len("/api/assignments/") : -len("/submit")])
                code = str(body.get("code") or "")
                result = self._run_assignment(user, assignment_id, code, run_all_cases=True)
                db.record_submission(user["id"], assignment_id, code, result)
                result["completed"] = bool(result.get("passed"))
                self._send_json(result)
            elif path == "/api/run":
                self._require_studio()
                self._send_json(self._run_code(body))
            elif path == "/api/test":
                self._require_studio()
                self._send_json(self._test_code(body))
            elif path == "/api/ai/draft":
                self._require_studio()
                self._send_json(self._ai_draft(body))
            elif path == "/api/projects":
                user = self._require_studio()
                self._send_json(db.save_project(user, body), status=HTTPStatus.CREATED)
            elif path == "/api/admin/users":
                self._require_admin()
                user = db.create_user(
                    username=str(body.get("username") or ""),
                    password=str(body.get("password") or ""),
                    display_name=str(body.get("display_name") or body.get("username") or ""),
                    role=str(body.get("role") or "student"),
                    must_change_password=True,
                )
                self._send_json({"user": db.public_user(user)}, status=HTTPStatus.CREATED)
            elif path == "/api/admin/unlock":
                admin = self._require_admin()
                db.unlock_assignment(int(body.get("user_id")), str(body.get("assignment_id")), admin["id"])
                self._send_json({"ok": True})
            elif path == "/api/admin/reset-password":
                self._require_admin()
                db.reset_password(int(body.get("user_id")), str(body.get("password") or ""))
                self._send_json({"ok": True})
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
        except ValueError as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        except PermissionError as exc:
            self._send_error(HTTPStatus.FORBIDDEN, str(exc))
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def _login(self, body: dict[str, Any]) -> None:
        user = db.authenticate(str(body.get("username") or ""), str(body.get("password") or ""))
        if not user:
            self._send_error(HTTPStatus.UNAUTHORIZED, "Invalid username or password")
            return
        token = db.create_session(user["id"])
        self._send_json({"user": db.public_user(user)}, headers=[_session_cookie(token)])

    def _logout(self) -> None:
        token = self._session_token()
        if token:
            db.delete_session(token)
        self._send_json({"ok": True}, headers=[_expired_session_cookie()])

    def _run_assignment(
        self,
        user: dict[str, Any],
        assignment_id: str,
        code: str,
        *,
        case_index: int = 0,
        run_all_cases: bool = False,
    ) -> dict[str, Any]:
        assignment = get_assignment(assignment_id)
        if not assignment or assignment.get("is_project"):
            raise ValueError("Assignment not found")
        if not db.is_assignment_unlocked(user, assignment_id):
            raise PermissionError("Assignment is locked")

        cases = assignment_cases(assignment, include_hidden=run_all_cases)
        if not cases:
            raise ValueError("Assignment has no test cases")
        selected_cases = cases if run_all_cases else [self._select_case(cases, case_index)]

        client = Judge0Client()
        case_payloads = [self._run_assignment_case(client, assignment, code, case) for case in selected_cases]

        if not run_all_cases:
            payload = case_payloads[0]
            payload["assignment_id"] = assignment_id
            payload["case_index"] = selected_cases[0]["index"]
            payload["case_results"] = [_case_summary(selected_cases[0], payload)]
            return payload

        passed = all(item.get("passed") for item in case_payloads)
        display_index = next((idx for idx, item in enumerate(case_payloads) if not item.get("passed")), 0)
        display_payload = case_payloads[display_index]
        case_results = [_case_summary(case, payload) for case, payload in zip(selected_cases, case_payloads)]
        stdout_parts = [item.get("stdout", "") for item in case_payloads if item.get("stdout")]
        return {
            "ok": all(item.get("ok") for item in case_payloads),
            "passed": passed,
            "assignment_id": assignment_id,
            "case_index": selected_cases[display_index]["index"],
            "case_name": selected_cases[display_index]["name"],
            "summary": {"passed": sum(1 for item in case_payloads if item.get("passed")), "total": len(case_payloads)},
            "checks": case_results,
            "case_results": case_results,
            "world": display_payload.get("world"),
            "trace": display_payload.get("trace", []),
            "stdout": "\n".join(stdout_parts),
            "error": display_payload.get("error", ""),
        }

    def _select_case(self, cases: list[dict[str, Any]], requested_index: int) -> dict[str, Any]:
        for case in cases:
            if case["index"] == requested_index:
                return case
        return cases[0]

    def _run_assignment_case(
        self,
        client: Judge0Client,
        assignment: dict[str, Any],
        code: str,
        case: dict[str, Any],
    ) -> dict[str, Any]:
        program = build_agent_program(code, assignment, world=case["world"], objectives=case["objectives"], case_name=case["name"])
        result = client.execute(program)
        payload, stdout = parse_result(result.get("stdout", ""))
        if not result.get("ok") and payload is None:
            payload = _execution_error(result)
            payload.setdefault("passed", False)
        elif payload is None:
            payload = {"ok": False, "passed": False, "error": "No AIP1 harness result was produced.", "stdout": stdout}
        if stdout:
            payload["stdout"] = "\n".join(item for item in [payload.get("stdout", ""), stdout] if item)
        payload["case_name"] = case["name"]
        payload["case_index"] = case["index"]
        return payload

    def _run_code(self, body: dict[str, Any]) -> dict[str, Any]:
        code = str(body.get("code") or "")
        actions = body.get("actions") or []
        if not isinstance(actions, list):
            raise ValueError("actions must be a list")
        program = build_play_program(code, [str(action) for action in actions])
        result = Judge0Client().execute(program)
        payload, stdout = parse_result(result.get("stdout", ""))
        if not result.get("ok") and payload is None:
            return _execution_error(result)
        if payload is None:
            return {"ok": False, "error": "No AIP1 harness result was produced.", "stdout": stdout}
        payload["stdout"] = stdout
        return payload

    def _test_code(self, body: dict[str, Any]) -> dict[str, Any]:
        code = str(body.get("code") or "")
        tests = _parse_tests(body.get("tests"))
        program = build_test_program(code, tests)
        result = Judge0Client().execute(program)
        payload, stdout = parse_result(result.get("stdout", ""))
        if not result.get("ok") and payload is None:
            return _execution_error(result)
        if payload is None:
            return {"ok": False, "error": "No AIP1 harness result was produced.", "stdout": stdout}
        payload["stdout"] = stdout
        return payload

    def _ai_draft(self, body: dict[str, Any]) -> dict[str, Any]:
        template = get_template(str(body.get("template_id") or "adventure"))
        spec = str(body.get("specification") or "").strip()
        if not spec:
            raise ValueError("A project specification is required before asking for AI help.")
        return draft_from_spec(
            mode=str(body.get("mode") or "code"),
            spec=spec,
            template_name=template["name"],
            current_code=str(body.get("code") or ""),
            current_tests=str(body.get("tests") or ""),
        )

    def _require_studio(self) -> dict[str, Any]:
        user = self._current_user()
        if not db.can_use_studio(user):
            raise PermissionError("Project Studio is locked until the beginner roadmap is complete")
        return user

    def _require_admin(self) -> dict[str, Any]:
        user = self._current_user()
        if user["role"] != "admin":
            raise PermissionError("Admin access required")
        return user

    def _current_user(self, required: bool = True) -> dict[str, Any] | None:
        user = db.user_for_session(self._session_token())
        if required and not user:
            raise PermissionError("Login required")
        return user

    def _session_token(self) -> str | None:
        cookie = SimpleCookie(self.headers.get("Cookie"))
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _send_json(
        self,
        payload: Any,
        status: HTTPStatus = HTTPStatus.OK,
        headers: list[tuple[str, str]] | None = None,
    ) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        for name, value in headers or []:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def _send_static(self, path: Path, base_dir: Path = STATIC_DIR) -> None:
        base = base_dir.resolve()
        resolved = path.resolve()
        if base not in resolved.parents and resolved != base:
            self._send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if not resolved.exists() or not resolved.is_file():
            self._send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def _case_summary(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary") or {}
    if summary:
        details = f"{summary.get('passed', 0)}/{summary.get('total', 0)} checks passed"
    else:
        details = payload.get("error") or ("passed" if payload.get("passed") else "failed")
    return {"name": case["name"], "passed": bool(payload.get("passed")), "details": details}


def _parse_tests(value: Any) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError("tests must be a JSON array")
    parsed = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("each test must be a JSON object")
        parsed.append(item)
    return parsed


def _execution_error(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status") or {}
    details = "\n".join(
        item
        for item in [
            f"Judge0 status: {status.get('description', 'Unknown')}",
            result.get("compile_output", ""),
            result.get("stderr", ""),
            result.get("message", ""),
        ]
        if item
    )
    return {"ok": False, "passed": False, "error": details or "Execution failed", "stdout": result.get("stdout", "")}


def _session_cookie(token: str) -> tuple[str, str]:
    return (
        "Set-Cookie",
        f"{SESSION_COOKIE}={token}; Path=/; Max-Age={db.SESSION_SECONDS}; HttpOnly; SameSite=Lax",
    )


def _expired_session_cookie() -> tuple[str, str]:
    return ("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")


def main() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    db.init_db()
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), StudioHandler)
    print(f"AIP1 Studio running at http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Judge0: {JUDGE0_HOST}:{JUDGE0_PORT}")
    print(f"LLM: {OPENAI_BASE_URL} ({OPENAI_MODEL})")
    print(f"SQLite: {db.DB_PATH}")
    server.serve_forever()
