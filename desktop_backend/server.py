from __future__ import annotations

import threading
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any, Callable

from storage.database import Database

from .runtime import DEFAULT_HOST, DEFAULT_PORT, select_runtime_port
from .server_routes import register_query_routes
from .server_runtime import build_request_handler

SERVICE_NAME = "desktop-backend"


class DesktopBackendServer:
    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        db: Database | None = None,
        task_registry: Any | None = None,
        get_handler: Callable[[str, dict[str, list[str]]], tuple[int, Any] | None] | None = None,
        post_handler: Callable[[str, dict[str, list[str]], Any], tuple[int, Any] | None] | None = None,
    ) -> None:
        self.host = host
        self.port = select_runtime_port(host=host, preferred_port=port)
        self._db = db
        self.task_registry = task_registry
        self._get_handler = get_handler
        self._post_handler = post_handler
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._routes: dict[tuple[str, str], Any] = {}
        register_query_routes(self)

    @property
    def db(self) -> Database:
        if self._db is None:
            self._db = Database()
        return self._db

    def _open_image_proxy(self, validated_url: str):
        req = urllib.request.Request(validated_url, headers={"Referer": "https://mp.weixin.qq.com/"})
        return urllib.request.urlopen(req, timeout=10)

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
        return build_request_handler(self, service_name=SERVICE_NAME)
