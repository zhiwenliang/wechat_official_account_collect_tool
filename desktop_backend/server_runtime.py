from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .http.image_proxy import (
    ImageProxyRequestError,
    read_image_proxy_response,
    validate_image_proxy_url,
)

from .server_json import json_bytes, read_json_body


def write_json(handler: BaseHTTPRequestHandler, status_code: int, payload: Any) -> None:
    body = json_bytes(payload)
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def handle_request(server: Any, handler: BaseHTTPRequestHandler, *, service_name: str) -> None:
    parsed = urlsplit(handler.path)
    path = parsed.path
    query = parse_qs(parsed.query)
    try:
        body = read_json_body(handler) if handler.command == "POST" else None
    except ValueError as exc:
        write_json(handler, 400, {"status": "error", "message": str(exc)})
        return

    if path == "/health":
        write_json(
            handler,
            200,
            {
                "status": "ok",
                "service": service_name,
            },
        )
        return

    if handler.command == "GET" and server._get_handler is not None:
        try:
            result = server._get_handler(path, query)
        except Exception as exc:
            write_json(handler, 500, {"status": "error", "message": str(exc)})
            return
        if result is not None:
            status_code, payload = result
            write_json(handler, status_code, payload)
            return

    if handler.command == "POST" and server._post_handler is not None:
        try:
            result = server._post_handler(path, query, body)
        except Exception as exc:
            write_json(handler, 500, {"status": "error", "message": str(exc)})
            return
        if result is not None:
            status_code, payload = result
            write_json(handler, status_code, payload)
            return

    if path == "/api/image-proxy":
        url = query.get("url", [""])[0]
        if not url:
            write_json(handler, 400, {"status": "error", "message": "missing url"})
            return
        try:
            validated_url = validate_image_proxy_url(url)
            with server._open_image_proxy(validated_url) as resp:
                data = read_image_proxy_response(resp)
                content_type = resp.headers.get("Content-Type", "image/jpeg")
            handler.send_response(200)
            handler.send_header("Content-Type", content_type)
            handler.send_header("Content-Length", str(len(data)))
            handler.send_header("Access-Control-Allow-Origin", "*")
            handler.send_header("Cache-Control", "public, max-age=86400")
            handler.end_headers()
            handler.wfile.write(data)
        except ImageProxyRequestError as exc:
            write_json(handler, exc.status_code, {"status": "error", "message": exc.message})
        except Exception:
            write_json(handler, 502, {"status": "error", "message": "failed to fetch image"})
        return

    route = server._routes.get((handler.command, path))
    if route is None:
        write_json(handler, 404, {"status": "error", "message": "not found"})
        return

    payload = route(query)
    if isinstance(payload, tuple) and len(payload) == 2 and isinstance(payload[0], int):
        status_code, response_payload = payload
        write_json(handler, status_code, response_payload)
        return

    write_json(handler, 200, payload)


def build_request_handler(server: Any, *, service_name: str):
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            handle_request(server, self, service_name=service_name)

        def do_POST(self) -> None:  # noqa: N802
            handle_request(server, self, service_name=service_name)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    return RequestHandler
