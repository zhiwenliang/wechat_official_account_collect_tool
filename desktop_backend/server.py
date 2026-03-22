from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from desktop_backend.query_handlers import (
    get_articles_handler,
    get_recent_articles_handler,
    get_statistics_handler,
)
from storage.database import Database

from .runtime import DEFAULT_HOST, DEFAULT_PORT, select_runtime_port

SERVICE_NAME = "desktop-backend"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class DesktopBackendServer:
    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        db: Database | None = None,
        task_registry: Any | None = None,
        post_handler: Callable[[str, dict[str, list[str]], Any], tuple[int, Any] | None] | None = None,
    ) -> None:
        self.host = host
        self.port = select_runtime_port(host=host, preferred_port=port)
        self._db = db
        self.task_registry = task_registry
        self._post_handler = post_handler
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._routes: dict[tuple[str, str], Any] = {}
        self._register_query_routes()

    @property
    def db(self) -> Database:
        if self._db is None:
            self._db = Database()
        return self._db

    def _register_query_routes(self) -> None:
        self._routes[("GET", "/api/statistics")] = lambda _query: get_statistics_handler(db=self.db)
        self._routes[("GET", "/api/recent-articles")] = lambda query: get_recent_articles_handler(
            db=self.db,
            limit=_parse_int(query, "limit", 5),
        )
        self._routes[("GET", "/api/articles")] = lambda query: get_articles_handler(
            db=self.db,
            status=query.get("status", ["all"])[0],
            search=query.get("search", [""])[0],
            page=_parse_int(query, "page", 1),
            page_size=_parse_int(query, "page_size", 20),
            sort_column=query.get("sort_column", [None])[0],
            descending=_parse_bool(query, "descending"),
        )

    def start(self) -> None:
        if self._httpd is not None:
            return

        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]

        self._thread = threading.Thread(target=self._httpd.serve_forever, name="desktop-backend", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return

        self._httpd.shutdown()
        self._httpd.server_close()

        if self._thread is not None:
            self._thread.join(timeout=5)

        self._httpd = None
        self._thread = None

    def serve_forever(self) -> None:
        self.start()
        self.wait()

    def wait(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def _build_handler(self):
        server = self

        class RequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                server._handle_request(self)

            def do_POST(self) -> None:  # noqa: N802
                server._handle_request(self)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        return RequestHandler

    def _handle_request(self, handler: BaseHTTPRequestHandler) -> None:
        parsed = urlsplit(handler.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            body = self._read_json_body(handler) if handler.command == "POST" else None
        except ValueError as exc:
            self._write_json(handler, 400, {"status": "error", "message": str(exc)})
            return

        if path == "/health":
            self._write_json(
                handler,
                200,
                {
                    "status": "ok",
                    "service": SERVICE_NAME,
                },
            )
            return

        if handler.command == "POST" and self._post_handler is not None:
            try:
                result = self._post_handler(path, query, body)
            except Exception as exc:
                self._write_json(handler, 500, {"status": "error", "message": str(exc)})
                return
            if result is not None:
                status_code, payload = result
                self._write_json(handler, status_code, payload)
                return

        route = self._routes.get((handler.command, path))
        if route is None:
            self._write_json(handler, 404, {"status": "error", "message": "not found"})
            return

        payload = route(query)
        self._write_json(handler, 200, payload)

    def _write_json(self, handler: BaseHTTPRequestHandler, status_code: int, payload: Any) -> None:
        body = _json_bytes(payload)
        handler.send_response(status_code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def _read_json_body(self, handler: BaseHTTPRequestHandler) -> Any:
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


def _parse_int(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(query.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def _parse_bool(query: dict[str, list[str]], key: str) -> bool:
    value = query.get(key, ["false"])[0]
    return str(value).lower() in {"1", "true", "yes", "on"}
