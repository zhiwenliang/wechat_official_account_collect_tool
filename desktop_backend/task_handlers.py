from __future__ import annotations

import queue
import threading
import time
from typing import Callable

from services.calibration_service import CalibrationCancelled, run_desktop_calibration_action
from services.workflows import run_collection_workflow, run_scrape_workflow

from .task_registry import TaskRegistry


CollectorFactory = Callable[[], object]
ScraperFactory = Callable[[], object]
DatabaseFactory = Callable[[], object]
FileStoreFactory = Callable[[], object]
PendingArticlesProvider = Callable[[], object]
CalibrationRuntimeFactory = Callable[[], object]


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


class _DesktopCalibrationRuntime:
    def __init__(self) -> None:
        import pyautogui

        self._pyautogui = pyautogui

    def get_current_position(self):
        return self._pyautogui.position()

    def click(self, x: int, y: int) -> None:
        self._pyautogui.click(x, y)

    def scroll(self, amount: int) -> None:
        self._pyautogui.scroll(amount)

    def move_to(self, x: int, y: int, duration: float) -> None:
        self._pyautogui.moveTo(x, y, duration)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def _default_calibration_runtime_factory():
    return _DesktopCalibrationRuntime()


class _CalibrationTaskWorker:
    def __init__(self, *, task_id: str, task_registry: TaskRegistry, action: str, runtime) -> None:
        self.task_id = task_id
        self.task_registry = task_registry
        self.action = action
        self.runtime = runtime
        self._responses: queue.Queue[dict[str, object]] = queue.Queue()
        self._cancelled = threading.Event()

    def stop(self) -> None:
        self._cancelled.set()
        self.task_registry.clear_prompt(self.task_id)
        self._responses.put({"response": "__cancel__"})

    def should_stop(self) -> bool:
        return self._cancelled.is_set() or self.task_registry.should_stop(self.task_id)

    def submit_response(self, response: dict[str, object]) -> bool:
        if self.should_stop() or not self.task_registry.is_active(self.task_id):
            return False
        self._responses.put(dict(response))
        return True

    def run(self):
        return run_desktop_calibration_action(
            action=self.action,
            request_position=self._request_position,
            request_ack=self._request_ack,
            request_integer=self._request_integer,
            request_confirm=self._request_confirm,
            get_current_position=self.runtime.get_current_position,
            click=self.runtime.click,
            scroll=self.runtime.scroll,
            move_to=self.runtime.move_to,
            sleep=self.runtime.sleep,
            log=lambda message: self.task_registry.record_log(self.task_id, message),
            status=lambda message: self.task_registry.record_status(self.task_id, "waiting", message),
            stop_checker=self.should_stop,
        )

    def _request_position(self, step: str, title: str, message: str):
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "position",
                "title": title,
                "message": message,
            },
        )
        self._await_response({"record"})
        position = self.runtime.get_current_position()
        self.task_registry.record_status(
            self.task_id,
            "recorded",
            f"已记录当前位置：({int(position.x)}, {int(position.y)})",
        )
        return position

    def _request_ack(self, step: str, title: str, message: str) -> bool:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "ack",
                "title": title,
                "message": message,
            },
        )
        self._await_response({"continue"})
        self.task_registry.record_status(self.task_id, "acknowledged", "已确认，继续下一步。")
        return True

    def _request_integer(self, step: str, title: str, message: str, default_value: int, min_value: int) -> int:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "integer",
                "title": title,
                "message": message,
                "default_value": default_value,
                "min_value": min_value,
            },
        )
        payload = self._await_response({"continue"})
        value = int(payload.get("value", default_value))
        self.task_registry.record_status(self.task_id, "recorded", f"已记录数值：{value}")
        return value

    def _request_confirm(self, step: str, title: str, message: str, confirm_label: str, reject_label: str) -> bool:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "confirm",
                "title": title,
                "message": message,
                "confirm_label": confirm_label,
                "reject_label": reject_label,
            },
        )
        payload = self._await_response({"confirm"})
        accepted = bool(payload.get("accepted"))
        outcome = "已确认通过。" if accepted else "已确认未通过。"
        self.task_registry.record_status(self.task_id, "confirmed", outcome)
        return accepted

    def _await_response(self, allowed_responses: set[str]) -> dict[str, object]:
        while True:
            if self.should_stop():
                raise CalibrationCancelled("cancelled")
            try:
                payload = self._responses.get(timeout=0.1)
            except queue.Empty:
                continue

            response_type = str(payload.get("response", ""))
            if response_type == "__cancel__":
                raise CalibrationCancelled("cancelled")
            if response_type not in allowed_responses:
                self.task_registry.record_status(
                    self.task_id,
                    "invalid_response",
                    f"当前步骤不接受操作：{response_type}",
                )
                continue

            self.task_registry.clear_prompt(self.task_id)
            return payload


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
        calibration_runtime_factory: CalibrationRuntimeFactory | None = None,
    ) -> None:
        self.task_registry = task_registry
        self._collector_factory = collector_factory or _default_collector_factory
        self._scraper_factory = scraper_factory or _default_scraper_factory
        self._scrape_db_factory = scrape_db_factory or _default_db_factory
        self._file_store_factory = file_store_factory or _default_file_store_factory
        self._pending_articles_provider = pending_articles_provider
        self._calibration_runtime_factory = calibration_runtime_factory or _default_calibration_runtime_factory
        self._active_workers: dict[str, object] = {}
        self._workers_lock = threading.RLock()

    def start_collection_task(self) -> str:
        collector = self._collector_factory()
        task_id = self.task_registry.start_task("collection")
        self._attach_stop_checker(task_id, collector)
        self._register_worker(task_id, collector)
        try:
            self._start_worker(
                task_id,
                target=lambda: self._run_collection_task(task_id, collector),
            )
        except Exception:
            self._clear_worker(task_id)
            self.task_registry.discard_task(task_id)
            raise
        return task_id

    def start_scrape_task(self) -> str:
        scraper = self._scraper_factory()
        db = self._scrape_db_factory()
        file_store = self._file_store_factory()
        pending_articles = self._pending_articles_provider() if self._pending_articles_provider else None
        task_id = self.task_registry.start_task("scrape")
        self._attach_stop_checker(task_id, scraper)
        self._register_worker(task_id, scraper)
        try:
            self._start_worker(
                task_id,
                target=lambda: self._run_scrape_task(task_id, db, file_store, scraper, pending_articles),
            )
        except Exception:
            self._clear_worker(task_id)
            self.task_registry.discard_task(task_id)
            raise
        return task_id

    def start_calibration_task(self, action: str) -> str:
        runtime = self._calibration_runtime_factory()
        task_id = self.task_registry.start_task("calibration")
        worker = _CalibrationTaskWorker(
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
        if not isinstance(worker, _CalibrationTaskWorker):
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

    def _run_collection_task(self, task_id: str, collector) -> None:
        try:
            result = run_collection_workflow(
                collector,
                log=lambda message: self.task_registry.record_log(task_id, message),
                progress=lambda current, total, message="", **kwargs: self.task_registry.record_progress(
                    task_id,
                    current,
                    total,
                    message,
                    success=kwargs.get("success"),
                    failed=kwargs.get("failed"),
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
                progress=lambda current, total, message="", **kwargs: self.task_registry.record_progress(
                    task_id,
                    current,
                    total,
                    message,
                    success=kwargs.get("success"),
                    failed=kwargs.get("failed"),
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

    def _run_calibration_task(self, task_id: str, action: str, worker: _CalibrationTaskWorker) -> None:
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
