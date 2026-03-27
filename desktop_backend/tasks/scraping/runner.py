from __future__ import annotations

from typing import Callable

from services.workflows import run_scrape_workflow

from ...task_registry import TaskRegistry


def begin_scrape_task(
    *,
    task_registry: TaskRegistry,
    db: object,
    file_store: object,
    scraper: object,
    pending_articles: object | None,
    attach_stop_checker: Callable[[str, object], None],
    register_worker: Callable[[str, object], None],
    start_worker: Callable[[str, Callable[[], None]], None],
    clear_worker: Callable[[str], None],
) -> str:
    task_id = task_registry.start_task("scrape")
    attach_stop_checker(task_id, scraper)
    register_worker(task_id, scraper)
    try:
        start_worker(
            task_id,
            lambda: run_scrape_task(
                task_id,
                db,
                file_store,
                scraper,
                pending_articles,
                task_registry=task_registry,
                clear_worker=clear_worker,
            ),
        )
    except Exception:
        clear_worker(task_id)
        task_registry.discard_task(task_id)
        raise
    return task_id


def run_scrape_task(
    task_id: str,
    db: object,
    file_store: object,
    scraper: object,
    pending_articles: object | None,
    *,
    task_registry: TaskRegistry,
    clear_worker: Callable[[str], None],
) -> None:
    def record_progress(current: int, total: int, message: str = "", **kwargs: object) -> None:
        task_registry.record_progress(
            task_id,
            current,
            total,
            message,
            success=kwargs.get("success"),
            failed=kwargs.get("failed"),
        )

    try:
        result = run_scrape_workflow(
            db=db,
            file_store=file_store,
            scraper=scraper,
            pending_articles=pending_articles,
            log=lambda message: task_registry.record_log(task_id, message),
            progress=record_progress,
            stop_checker=lambda: task_registry.should_stop(task_id),
        )
    except Exception as exc:
        task_registry.record_error(task_id, str(exc))
        return
    finally:
        clear_worker(task_id)

    if result.stopped:
        task_registry.record_stopped(task_id, "stop requested")
        return

    task_registry.record_completed(task_id)
