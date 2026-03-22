from __future__ import annotations

import threading
from typing import Callable

from services.workflows import run_collection_workflow, run_scrape_workflow

from .task_registry import TaskRegistry


CollectorFactory = Callable[[], object]
ScraperFactory = Callable[[], object]
DatabaseFactory = Callable[[], object]
FileStoreFactory = Callable[[], object]
PendingArticlesProvider = Callable[[], object]


def _default_collector_factory():
    from scraper.link_collector import LinkCollector

    return LinkCollector()


def _default_scraper_factory():
    from scraper.content_scraper import ContentScraper

    return ContentScraper()


def _default_db_factory():
    from storage.database import Database

    return Database()


def _default_file_store_factory():
    from storage.file_store import FileStore

    return FileStore()


class WorkflowTaskHandlers:
    def __init__(
        self,
        *,
        task_registry: TaskRegistry,
        collector_factory: CollectorFactory | None = None,
        scraper_factory: ScraperFactory | None = None,
        scrape_db_factory: DatabaseFactory | None = None,
        file_store_factory: FileStoreFactory | None = None,
        pending_articles_provider: PendingArticlesProvider | None = None,
    ) -> None:
        self.task_registry = task_registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._scraper_factory = scraper_factory or _default_scraper_factory
        self._scrape_db_factory = scrape_db_factory or _default_db_factory
        self._file_store_factory = file_store_factory or _default_file_store_factory
        self._pending_articles_provider = pending_articles_provider
        self._active_workers: dict[str, object] = {}
        self._workers_lock = threading.RLock()

    def start_collection_task(self) -> str:
        collector = self._collector_factory()
        task_id = self.task_registry.start_task("collection")
        self._attach_stop_checker(task_id, collector)
        self._register_worker(task_id, collector)

        self._start_worker(
            task_id,
            target=lambda: self._run_collection_task(task_id, collector),
        )
        return task_id

    def start_scrape_task(self) -> str:
        scraper = self._scraper_factory()
        db = self._scrape_db_factory()
        file_store = self._file_store_factory()
        pending_articles = self._pending_articles_provider() if self._pending_articles_provider else None
        task_id = self.task_registry.start_task("scrape")
        self._attach_stop_checker(task_id, scraper)
        self._register_worker(task_id, scraper)

        self._start_worker(
            task_id,
            target=lambda: self._run_scrape_task(task_id, db, file_store, scraper, pending_articles),
        )
        return task_id

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

    def _run_collection_task(self, task_id: str, collector) -> None:
        try:
            result = run_collection_workflow(
                collector,
                log=lambda message: self.task_registry.record_log(task_id, message),
                progress=lambda current, total, message="", **_kwargs: self.task_registry.record_progress(
                    task_id,
                    current,
                    total,
                    message,
                ),
                stop_checker=lambda: self.task_registry.should_stop(task_id),
            )
        except Exception as exc:
            self.task_registry.record_error(task_id, str(exc))
            return
        finally:
            self._clear_worker(task_id)

        if result.stopped:
            self.task_registry.record_stopped(task_id, "stop requested")
            return

        self.task_registry.record_completed(task_id)

    def _run_scrape_task(self, task_id: str, db, file_store, scraper, pending_articles) -> None:
        try:
            result = run_scrape_workflow(
                db=db,
                file_store=file_store,
                scraper=scraper,
                pending_articles=pending_articles,
                log=lambda message: self.task_registry.record_log(task_id, message),
                progress=lambda current, total, message="", **_kwargs: self.task_registry.record_progress(
                    task_id,
                    current,
                    total,
                    message,
                ),
                stop_checker=lambda: self.task_registry.should_stop(task_id),
            )
        except Exception as exc:
            self.task_registry.record_error(task_id, str(exc))
            return
        finally:
            self._clear_worker(task_id)

        if result.stopped:
            self.task_registry.record_stopped(task_id, "stop requested")
            return

        self.task_registry.record_completed(task_id)
