from __future__ import annotations

from typing import Callable

from services.workflows import run_collection_workflow

from ...task_registry import TaskRegistry


def begin_collection_task(
    *,
    task_registry: TaskRegistry,
    collector: object,
    attach_stop_checker: Callable[[str, object], None],
    register_worker: Callable[[str, object], None],
    start_worker: Callable[[str, Callable[[], None]], None],
    clear_worker: Callable[[str], None],
) -> str:
    task_id = task_registry.start_task("collection")
    attach_stop_checker(task_id, collector)
    register_worker(task_id, collector)
    try:
        start_worker(
            task_id,
            lambda: run_collection_task(
                task_id,
                collector,
                task_registry=task_registry,
                clear_worker=clear_worker,
            ),
        )
    except Exception:
        clear_worker(task_id)
        task_registry.discard_task(task_id)
        raise
    return task_id


def run_collection_task(
    task_id: str,
    collector: object,
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
        result = run_collection_workflow(
            collector,
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
