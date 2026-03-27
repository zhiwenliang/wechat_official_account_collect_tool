from __future__ import annotations

import threading
from typing import Callable

from services.calibration_service import CalibrationCancelled

from ..task_registry import TaskRegistry
from .calibration.runtime import default_calibration_runtime_factory
from .calibration.worker import CalibrationTaskWorker
from .collection.runner import begin_collection_task
from .scraping.runner import begin_scrape_task
from .defaults import (
    CalibrationRuntimeFactory,
    CollectorFactory,
    DatabaseFactory,
    FileStoreFactory,
    PendingArticlesProvider,
    ScraperFactory,
    default_collector_factory,
    default_db_factory,
    default_file_store_factory,
    default_scraper_factory,
)


class WorkflowTaskHandlersImpl:
    def __init__(
        self,
        *,
        task_registry: TaskRegistry,
        collector_factory: CollectorFactory | None = None,
        scraper_factory: ScraperFactory | None = None,
        scrape_db_factory: DatabaseFactory | None = None,
        file_store_factory: FileStoreFactory | None = None,
        pending_articles_provider: PendingArticlesProvider | None = None,
        calibration_runtime_factory: CalibrationRuntimeFactory | None = None,
    ) -> None:
        self.task_registry = task_registry
        self._collector_factory = collector_factory or default_collector_factory
        self._scraper_factory = scraper_factory or default_scraper_factory
        self._scrape_db_factory = scrape_db_factory or default_db_factory
        self._file_store_factory = file_store_factory or default_file_store_factory
        self._pending_articles_provider = pending_articles_provider
        self._calibration_runtime_factory = calibration_runtime_factory or default_calibration_runtime_factory
        self._active_workers: dict[str, object] = {}
        self._workers_lock = threading.RLock()

    def start_collection_task(self) -> str:
        collector = self._collector_factory()
        return begin_collection_task(
            task_registry=self.task_registry,
            collector=collector,
            attach_stop_checker=self._attach_stop_checker,
            register_worker=self._register_worker,
            start_worker=lambda tid, tgt: self._start_worker(tid, target=tgt),
            clear_worker=self._clear_worker,
        )

    def start_scrape_task(self) -> str:
        scraper = self._scraper_factory()
        db = self._scrape_db_factory()
        file_store = self._file_store_factory()
        pending_articles = self._pending_articles_provider() if self._pending_articles_provider else None
        return begin_scrape_task(
            task_registry=self.task_registry,
            db=db,
            file_store=file_store,
            scraper=scraper,
            pending_articles=pending_articles,
            attach_stop_checker=self._attach_stop_checker,
            register_worker=self._register_worker,
            start_worker=lambda tid, tgt: self._start_worker(tid, target=tgt),
            clear_worker=self._clear_worker,
        )

    def start_calibration_task(self, action: str) -> str:
        runtime = self._calibration_runtime_factory()
        task_id = self.task_registry.start_task("calibration")
        worker = CalibrationTaskWorker(
            task_id=task_id,
            task_registry=self.task_registry,
            action=str(action),
            runtime=runtime,
        )
        self._register_worker(task_id, worker)
        try:
            self._start_worker(
                task_id,
                target=lambda: self._run_calibration_task(task_id, action, worker),
            )
        except Exception:
            self._clear_worker(task_id)
            self.task_registry.discard_task(task_id)
            raise
        return task_id

    def submit_calibration_response(self, task_id: str, response: dict[str, object]) -> bool:
        worker = self._get_worker(task_id)
        if not isinstance(worker, CalibrationTaskWorker):
            return False
        return worker.submit_response(response)

    def request_stop(self, task_id: str) -> bool:
        if not self.task_registry.is_active(task_id):
            return False
        self.task_registry.request_stop(task_id)
        worker = self._get_worker(task_id)
        if worker is not None:
            stop = getattr(worker, "stop", None)
            if callable(stop):
                stop()
        return True

    def _start_worker(self, task_id: str, *, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, name=f"desktop-task-{task_id}", daemon=True)
        thread.start()

    def _attach_stop_checker(self, task_id: str, worker) -> None:
        stop_checker = lambda: self.task_registry.should_stop(task_id)

        if hasattr(worker, "stop_checker"):
            worker.stop_checker = stop_checker

        stop = getattr(worker, "stop", None)
        if callable(stop):
            stop_lock = threading.Lock()
            stop_called = False

            def stop_once():
                nonlocal stop_called
                with stop_lock:
                    if stop_called:
                        return None
                    stop_called = True
                return stop()

            worker.stop = stop_once

        original_should_stop = getattr(worker, "should_stop", None)
        if callable(original_should_stop):
            worker.should_stop = lambda: bool(stop_checker() or original_should_stop())

    def _register_worker(self, task_id: str, worker: object) -> None:
        with self._workers_lock:
            self._active_workers[task_id] = worker

    def _get_worker(self, task_id: str) -> object | None:
        with self._workers_lock:
            return self._active_workers.get(task_id)

    def _clear_worker(self, task_id: str) -> None:
        with self._workers_lock:
            self._active_workers.pop(task_id, None)

    def _run_calibration_task(self, task_id: str, action: str, worker: CalibrationTaskWorker) -> None:
        try:
            result = worker.run()
        except CalibrationCancelled:
            self.task_registry.record_cancelled(task_id, "user cancelled")
            return
        except Exception as exc:
            self.task_registry.record_error(task_id, str(exc))
            return
        finally:
            self._clear_worker(task_id)

        if action == "test":
            if result is False:
                self.task_registry.record_status(task_id, "test_failed", "校准测试未通过")
            elif result is True:
                self.task_registry.record_status(task_id, "test_passed", "校准测试通过")

        self.task_registry.record_completed(task_id)
