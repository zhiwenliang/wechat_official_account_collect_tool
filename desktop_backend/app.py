from __future__ import annotations

import argparse
from typing import Any

from .runtime import DEFAULT_HOST, DEFAULT_PORT
from .server import DesktopBackendServer
from .task_handlers import WorkflowTaskHandlers
from .task_registry import TaskRegistry


def create_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    collector_factory=None,
    scraper_factory=None,
    scrape_db_factory=None,
    file_store_factory=None,
    pending_articles_provider=None,
) -> DesktopBackendServer:
    task_registry = TaskRegistry()
    task_handlers = WorkflowTaskHandlers(
        task_registry=task_registry,
        collector_factory=collector_factory,
        scraper_factory=scraper_factory,
        scrape_db_factory=scrape_db_factory,
        file_store_factory=file_store_factory,
        pending_articles_provider=pending_articles_provider,
    )

    return DesktopBackendServer(
        host=host,
        port=port,
        task_registry=task_registry,
        post_handler=lambda path, _query, _body: _handle_post(path, task_handlers),
    )


def _handle_post(path: str, task_handlers: WorkflowTaskHandlers) -> tuple[int, dict[str, Any]] | None:
    if path == "/tasks/collection":
        task_id = task_handlers.start_collection_task()
        return 202, {"task_id": task_id}

    if path == "/tasks/scrape":
        task_id = task_handlers.start_scrape_task()
        return 202, {"task_id": task_id}

    if path.startswith("/tasks/") and path.endswith("/stop"):
        task_id = path[len("/tasks/") : -len("/stop")].strip("/")
        stopping = task_handlers.request_stop(task_id)
        if not stopping:
            return 404, {"status": "error", "message": "task not found", "task_id": task_id}
        return 202, {"task_id": task_id, "stopping": True}

    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the desktop backend sidecar server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred port to bind.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    server = create_server(host=args.host, port=args.port)

    try:
        server.start()
        print(f"desktop-backend listening on http://{server.host}:{server.port}")
        server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
