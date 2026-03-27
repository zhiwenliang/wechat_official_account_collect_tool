from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Any


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def read_json_body(handler: BaseHTTPRequestHandler) -> Any:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}
    raw_body = handler.rfile.read(content_length)
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid json body") from exc
