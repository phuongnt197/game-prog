from __future__ import annotations

import base64
import json
from typing import Any


RESULT_PREFIX = "__AIP1_STUDIO_RESULT__"


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
