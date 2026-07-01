from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .config import (
    JUDGE0_HOST,
    JUDGE0_PORT,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    SERVER_HOST,
    SERVER_PORT,
    STATIC_DIR,
)
from .harness import build_play_program, build_test_program, parse_result
from .judge0 import Judge0Client
from .llm import draft_from_spec
from .projects import get_project, list_projects, save_project
from .templates import get_template, template_list


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "AIP1Studio/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._send_static(STATIC_DIR / "index.html")
        elif path.startswith("/static/"):
            self._send_static(STATIC_DIR / unquote(path.removeprefix("/static/")))
        elif path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "judge0": f"{JUDGE0_HOST}:{JUDGE0_PORT}",
                    "openai_base_url": OPENAI_BASE_URL,
                    "openai_model": OPENAI_MODEL,
                }
            )
        elif path == "/api/templates":
            self._send_json({"templates": template_list()})
        elif path.startswith("/api/templates/"):
            template_id = unquote(path.removeprefix("/api/templates/"))
            self._send_json(get_template(template_id))
        elif path == "/api/projects":
            self._send_json({"projects": list_projects()})
        elif path.startswith("/api/projects/"):
            slug = unquote(path.removeprefix("/api/projects/"))
            project = get_project(slug)
            if not project:
                self._send_error(HTTPStatus.NOT_FOUND, "Project not found")
            else:
                self._send_json(project)
        else:
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            body = self._read_json()
            if path == "/api/run":
                self._send_json(self._run_code(body))
            elif path == "/api/test":
                self._send_json(self._test_code(body))
            elif path == "/api/ai/draft":
                self._send_json(self._ai_draft(body))
            elif path == "/api/projects":
                self._send_json(save_project(body), status=HTTPStatus.CREATED)
            else:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
        except ValueError as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

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

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def _send_static(self, path: Path) -> None:
        base = STATIC_DIR.resolve()
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
    return {"ok": False, "error": details or "Execution failed", "stdout": result.get("stdout", "")}


def main() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), StudioHandler)
    print(f"AIP1 Studio running at http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Judge0: {JUDGE0_HOST}:{JUDGE0_PORT}")
    print(f"LLM: {OPENAI_BASE_URL} ({OPENAI_MODEL})")
    server.serve_forever()
