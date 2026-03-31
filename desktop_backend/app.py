from __future__ import annotations

import argparse
from typing import Any

from .runtime import DEFAULT_HOST, DEFAULT_PORT
from .server import DesktopBackendServer
from .import_export_handlers import export_data_bundle_handler, import_database_handler
from .articles.command_handlers import (
    delete_selected_articles_handler,
    retry_empty_content_articles_handler,
    retry_failed_articles_handler,
)
from .task_registry import TaskRegistry
from .tasks.workflow_handlers import WorkflowTaskHandlers


def create_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    collector_factory=None,
    scraper_factory=None,
    scrape_db_factory=None,
    file_store_factory=None,
    pending_articles_provider=None,
    calibration_runtime_factory=None,
) -> DesktopBackendServer:
    task_registry = TaskRegistry()
    task_handlers = WorkflowTaskHandlers(
        task_registry=task_registry,
        collector_factory=collector_factory,
        scraper_factory=scraper_factory,
        scrape_db_factory=scrape_db_factory,
        file_store_factory=file_store_factory,
        pending_articles_provider=pending_articles_provider,
        calibration_runtime_factory=calibration_runtime_factory,
    )

    return DesktopBackendServer(
        host=host,
        port=port,
        task_registry=task_registry,
        get_handler=lambda path, _query: _handle_get(path, task_registry),
        post_handler=lambda path, _query, body: _handle_post(path, body, task_handlers),
    )


def _handle_get(
    path: str,
    task_registry: TaskRegistry,
) -> tuple[int, dict[str, Any]] | None:
    if not path.startswith("/tasks/") or path.count("/") != 2:
        return None

    task_id = path[len("/tasks/") :].strip("/")
    if not task_id:
        return 404, {"status": "error", "message": "task not found", "task_id": task_id}

    snapshot = task_registry.snapshot_task(task_id)
    if snapshot is None:
        return 404, {"status": "error", "message": "task not found", "task_id": task_id}

    return 200, {
        "task_id": snapshot.task_id,
        "task_type": snapshot.task_type,
        "active": snapshot.active,
        "stopping": snapshot.stopping,
        "prompt": snapshot.prompt,
        "events": snapshot.events,
    }


def _handle_post(
    path: str,
    body: Any,
    task_handlers: WorkflowTaskHandlers,
) -> tuple[int, dict[str, Any]] | None:
    payload = body if isinstance(body, dict) else {}

    if path == "/api/articles/retry-failed":
        result = retry_failed_articles_handler()
        return 200, {"status": "ok", **result}

    if path == "/api/articles/retry-empty-content":
        result = retry_empty_content_articles_handler()
        return 200, {"status": "ok", **result}

    if path == "/api/articles/delete":
        article_ids = payload.get("article_ids")
        if not isinstance(article_ids, list) or not article_ids:
            return 400, {"status": "error", "message": "article_ids must be a non-empty list"}
        try:
            result = delete_selected_articles_handler(article_ids=article_ids)
        except (TypeError, ValueError) as exc:
            return 400, {"status": "error", "message": str(exc)}
        return 200, {"status": "ok", **result}

    if path == "/api/data/export":
        output_path = payload.get("output_path")
        if not output_path:
            return 400, {"status": "error", "message": "output_path is required"}
        try:
            result = export_data_bundle_handler(
                output_path=output_path,
                db_path=payload.get("db_path"),
                articles_dir=payload.get("articles_dir"),
            )
        except (FileNotFoundError, ValueError) as exc:
            return 400, {"status": "error", "message": str(exc)}
        return 200, {"status": "ok", **result}

    if path == "/api/data/import":
        source_db_path = payload.get("source_db_path")
        if not source_db_path:
            return 400, {"status": "error", "message": "source_db_path is required"}
        try:
            result = import_database_handler(
                source_db_path=source_db_path,
                target_db_path=payload.get("target_db_path"),
            )
        except (FileNotFoundError, ValueError) as exc:
            return 400, {"status": "error", "message": str(exc)}
        return 200, {"status": "ok", **result}

    if path == "/tasks/collection":
        task_id = task_handlers.start_collection_task()
        return 202, {"task_id": task_id}

    if path == "/tasks/scrape":
        task_id = task_handlers.start_scrape_task()
        return 202, {"task_id": task_id}

    if path == "/tasks/calibration":
        action = payload.get("action")
        if not action:
            return 400, {"status": "error", "message": "action is required"}
        task_id = task_handlers.start_calibration_task(str(action))
        return 202, {"task_id": task_id}

    if path.startswith("/tasks/") and path.endswith("/stop"):
        task_id = path[len("/tasks/") : -len("/stop")].strip("/")
        stopping = task_handlers.request_stop(task_id)
        if not stopping:
            return 404, {"status": "error", "message": "task not found", "task_id": task_id}
        return 202, {"task_id": task_id, "stopping": True}

    if path.startswith("/tasks/") and path.endswith("/respond"):
        task_id = path[len("/tasks/") : -len("/respond")].strip("/")
        accepted = task_handlers.submit_calibration_response(task_id, payload)
        if not accepted:
            return 404, {"status": "error", "message": "task not found", "task_id": task_id}
        return 202, {"task_id": task_id, "accepted": True}

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
