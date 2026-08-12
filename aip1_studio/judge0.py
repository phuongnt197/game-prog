from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .config import (
    JUDGE0_HOST,
    JUDGE0_LANGUAGE_ID,
    JUDGE0_MEMORY_LIMIT,
    JUDGE0_POLL_INTERVAL,
    JUDGE0_PORT,
    JUDGE0_TIME_LIMIT,
)


def _decode_b64(value: str | None) -> str:
    if not value:
        return ""
    try:
        return base64.b64decode(value).decode("utf-8", errors="replace")
    except Exception:
        return value


@dataclass
class Judge0Client:
    host: str = JUDGE0_HOST
    port: int = JUDGE0_PORT
    language_id: int = JUDGE0_LANGUAGE_ID
    poll_interval: float = JUDGE0_POLL_INTERVAL
    time_limit: float = JUDGE0_TIME_LIMIT
    memory_limit: int = JUDGE0_MEMORY_LIMIT

    @property
    def base_url(self) -> str:
        return f"{self.host}:{self.port}"

    def execute(self, source_code: str) -> dict[str, Any]:
        payload = {
            "language_id": self.language_id,
            "source_code": base64.b64encode(source_code.encode("utf-8")).decode("ascii"),
            "cpu_time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
        }
        submission = self._request_json(
            "POST",
            f"{self.base_url}/submissions"
            "?base64_encoded=true&fields=token,stdout,stderr,status,compile_output,message",
            payload,
        )
        token = submission.get("token")
        if not token:
            raise RuntimeError(f"Judge0 did not return a token: {submission}")

        result = self._poll(token)
        status = result.get("status") or {}
        return {
            "ok": status.get("id") == 3,
            "status": status,
            "stdout": _decode_b64(result.get("stdout")),
            "stderr": _decode_b64(result.get("stderr")),
            "compile_output": _decode_b64(result.get("compile_output")),
            "message": _decode_b64(result.get("message")),
            "raw": result,
        }

    def _poll(self, token: str) -> dict[str, Any]:
        url = (
            f"{self.base_url}/submissions/{token}"
            "?base64_encoded=true&fields=stdout,stderr,status,compile_output,message"
        )
        while True:
            result = self._request_json("GET", url)
            status_id = (result.get("status") or {}).get("id")
            if status_id not in (1, 2):
                return result
            time.sleep(self.poll_interval)

    @staticmethod
    def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                data = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Judge0 HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Judge0 request failed: {exc.reason}") from exc
        return json.loads(data or "{}")
