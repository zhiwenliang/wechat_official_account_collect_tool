# Phase 4 Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining migration-era compatibility modules, relocate shared statistics into a final home, and leave the repo with one canonical import path per responsibility without changing runtime behavior.

**Architecture:** Phase 4 completes the migration in small, behavior-preserving slices. First introduce the final canonical modules for shared statistics and task orchestration, then repoint imports/tests to those modules, then delete shim-only modules, and finally align active contributor docs with the final tree.

**Tech Stack:** Python 3.10, stdlib HTTP server, `unittest`, `rg`, Electron desktop app, TypeScript/Vitest

---

## File Structure

- `desktop_backend/statistics.py`: final home for `StatisticsPayload`, `build_statistics_payload`, and `get_statistics_handler`.
- `desktop_backend/articles/`: canonical article query/command handlers and payload builders; no fallback barrel imports remain after this phase.
- `desktop_backend/task_registry.py`: canonical shared task registry path.
- `desktop_backend/task_events.py`: canonical shared task event path.
- `desktop_backend/tasks/workflow_handlers.py`: canonical shared task orchestration module replacing the migration-era handler shims.
- `desktop_backend/tasks/calibration/worker.py`: canonical calibration worker path.
- `tests/test_desktop_backend_structure.py`: direct ownership/contract checks for the final module layout.
- `tests/test_desktop_backend_queries.py`: behavior coverage for statistics and article queries using only final import paths.
- `tests/test_desktop_backend_tasks.py`: task-route regression coverage using only final orchestration imports.
- `tests/test_electron_only_repo.py`: active-doc guardrails for final structure guidance.
- `README.md`, `AGENTS.md`, `CLAUDE.md`: active contributor docs that must describe the same final layout and avoid removed shim paths.

### Task 1: Introduce Final Statistics Module

**Files:**
- Create: `desktop_backend/statistics.py`
- Modify: `desktop_backend/server_routes.py`
- Modify: `tests/test_desktop_backend_queries.py`
- Modify: `tests/test_desktop_backend_structure.py`
- Test: `tests/test_desktop_backend_queries.py`
- Test: `tests/test_desktop_backend_structure.py`

- [ ] **Step 1: Write the failing statistics-module tests**

```python
from desktop_backend.statistics import get_statistics_handler

class DesktopBackendQueryTests(unittest.TestCase):
    def test_get_statistics_returns_expected_counts(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db = make_database(root)
        seed_article(db, url="https://example.com/1")

        result = get_statistics_handler(db=db)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["pending"], 1)


class DesktopBackendStructureTests(unittest.TestCase):
    def test_statistics_module_exists(self) -> None:
        from desktop_backend.statistics import (
            StatisticsPayload,
            build_statistics_payload,
            get_statistics_handler,
        )

        sample: StatisticsPayload = build_statistics_payload({"total": 2, "failed_urls": ["x"]})
        self.assertEqual(sample["total"], 2)
        self.assertEqual(sample["failed_urls"], ["x"])
        self.assertTrue(callable(get_statistics_handler))
```

- [ ] **Step 2: Run the targeted Python tests and confirm they fail**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries tests.test_desktop_backend_structure -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'desktop_backend.statistics'`

- [ ] **Step 3: Add the canonical statistics implementation and repoint the route import**

```python
# desktop_backend/statistics.py
from typing import Any, TypedDict

from storage.database import Database


class StatisticsPayload(TypedDict):
    total: int
    pending: int
    scraped: int
    failed: int
    empty_content: int
    failed_urls: list[str]


def build_statistics_payload(stats: dict[str, Any]) -> StatisticsPayload:
    return {
        "total": int(stats.get("total", 0)),
        "pending": int(stats.get("pending", 0)),
        "scraped": int(stats.get("scraped", 0)),
        "failed": int(stats.get("failed", 0)),
        "empty_content": int(stats.get("empty_content", 0)),
        "failed_urls": list(stats.get("failed_urls", [])),
    }


def get_statistics_handler(*, db: Database) -> StatisticsPayload:
    return build_statistics_payload(db.get_statistics())
```

```python
# desktop_backend/server_routes.py
from desktop_backend.articles.query_handlers import (
    get_article_detail_handler,
    get_articles_handler,
    get_recent_articles_handler,
)
from desktop_backend.statistics import get_statistics_handler


def register_query_routes(server) -> None:
    server._routes[("GET", "/api/statistics")] = lambda _query: get_statistics_handler(db=server.db)
```

- [ ] **Step 4: Run the route and query regressions**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries tests.test_desktop_backend_structure tests.test_desktop_backend_server -v`

Expected: PASS for the statistics behavior tests, structure test, and server route regressions

- [ ] **Step 5: Commit the statistics relocation**

```bash
git add desktop_backend/statistics.py desktop_backend/server_routes.py tests/test_desktop_backend_queries.py tests/test_desktop_backend_structure.py
git commit -m "refactor: move statistics into final sidecar module"
```

### Task 2: Canonicalize Task Infrastructure Imports

**Files:**
- Create: `desktop_backend/tasks/workflow_handlers.py`
- Modify: `desktop_backend/app.py`
- Modify: `tests/test_desktop_backend_structure.py`
- Modify: `tests/test_desktop_backend_tasks.py`
- Delete: `desktop_backend/task_handlers.py`
- Delete: `desktop_backend/tasks/__init__.py`
- Delete: `desktop_backend/tasks/events.py`
- Delete: `desktop_backend/tasks/handlers.py`
- Delete: `desktop_backend/tasks/registry.py`
- Delete: `desktop_backend/tasks/calibration_worker.py`
- Delete: `desktop_backend/tasks/workflow_handlers_impl.py`
- Test: `tests/test_desktop_backend_structure.py`
- Test: `tests/test_desktop_backend_tasks.py`

- [ ] **Step 1: Rewrite the structure/task tests to expect final canonical imports**

```python
class DesktopBackendStructureTests(unittest.TestCase):
    def test_task_infrastructure_modules_exist(self) -> None:
        from desktop_backend.task_events import build_started_event
        from desktop_backend.task_registry import TaskRegistry
        from desktop_backend.tasks.calibration.runtime import default_calibration_runtime_factory
        from desktop_backend.tasks.calibration.status import get_calibration_status_handler
        from desktop_backend.tasks.calibration.worker import CalibrationTaskWorker
        from desktop_backend.tasks.workflow_handlers import WorkflowTaskHandlers

        self.assertTrue(callable(build_started_event))
        self.assertTrue(callable(get_calibration_status_handler))
        self.assertTrue(hasattr(TaskRegistry, "start_task"))
        self.assertTrue(hasattr(WorkflowTaskHandlers, "start_collection_task"))
        self.assertTrue(hasattr(CalibrationTaskWorker, "submit_response"))
        self.assertTrue(callable(default_calibration_runtime_factory))
```

```python
# tests/test_desktop_backend_tasks.py
from desktop_backend.tasks.workflow_handlers import WorkflowTaskHandlers

with mock.patch.object(
    WorkflowTaskHandlers,
    "_start_worker",
    side_effect=RuntimeError("cannot start thread"),
):
    with self.assertRaises(urllib.error.HTTPError):
        urllib.request.urlopen(request, timeout=2)
```

- [ ] **Step 2: Run the targeted task tests and confirm they fail**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure tests.test_desktop_backend_tasks -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'desktop_backend.tasks.workflow_handlers'`

- [ ] **Step 3: Create the final orchestration module and repoint the app imports**

```python
# desktop_backend/tasks/workflow_handlers.py
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
```

```python
# desktop_backend/app.py
from .task_registry import TaskRegistry
from .tasks.workflow_handlers import WorkflowTaskHandlers
```

- [ ] **Step 4: Delete the shim-only task modules after the imports are repointed**

```python
# deleted files
# - desktop_backend/task_handlers.py
# - desktop_backend/tasks/__init__.py
# - desktop_backend/tasks/events.py
# - desktop_backend/tasks/handlers.py
# - desktop_backend/tasks/registry.py
# - desktop_backend/tasks/calibration_worker.py
# - desktop_backend/tasks/workflow_handlers_impl.py
```

- [ ] **Step 5: Run the task regression suite**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure tests.test_desktop_backend_tasks -v`

Expected: PASS with the canonical task imports only

- [ ] **Step 6: Search the repo for deleted task shim references**

Run: `rg "desktop_backend\.task_handlers|desktop_backend\.tasks\.(handlers|registry|events|calibration_worker)|workflow_handlers_impl" desktop_backend tests`

Expected: no matches

- [ ] **Step 7: Commit the task infrastructure cleanup**

```bash
git add desktop_backend/app.py desktop_backend/task_registry.py desktop_backend/task_events.py desktop_backend/tasks tests/test_desktop_backend_structure.py tests/test_desktop_backend_tasks.py
git commit -m "refactor: remove task compatibility shims"
```

### Task 3: Remove Legacy Article and Schema Barrels

**Files:**
- Modify: `tests/test_desktop_backend_queries.py`
- Modify: `tests/test_desktop_backend_structure.py`
- Modify: `desktop_backend/__init__.py`
- Delete: `desktop_backend/query_handlers.py`
- Delete: `desktop_backend/schemas.py`
- Test: `tests/test_desktop_backend_queries.py`
- Test: `tests/test_desktop_backend_structure.py`

- [ ] **Step 1: Add a failing package-surface test and switch article-detail imports to final paths**

```python
# tests/test_desktop_backend_queries.py
from desktop_backend.articles.query_handlers import (
    get_article_detail_handler,
    get_articles_handler,
    get_recent_articles_handler,
)
from desktop_backend.statistics import get_statistics_handler
```

```python
class DesktopBackendStructureTests(unittest.TestCase):
    def test_desktop_backend_package_does_not_re_export_migration_aliases(self) -> None:
        import desktop_backend

        self.assertFalse(hasattr(desktop_backend, "get_articles_handler"))
        self.assertFalse(hasattr(desktop_backend, "get_recent_articles_handler"))
        self.assertFalse(hasattr(desktop_backend, "get_statistics_handler"))
```

- [ ] **Step 2: Run the structure/query tests and confirm they fail**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries tests.test_desktop_backend_structure -v`

Expected: FAIL because `desktop_backend.__init__` still exposes migration-era re-exports

- [ ] **Step 3: Remove the article/query/schema barrels and keep the package root minimal**

```python
# desktop_backend/__init__.py
"""Desktop backend package for the Electron sidecar."""
```

```python
# deleted files
# - desktop_backend/query_handlers.py
# - desktop_backend/schemas.py
```

- [ ] **Step 4: Rewrite the structure test to assert final ownership directly**

```python
class DesktopBackendStructureTests(unittest.TestCase):
    def test_articles_domain_modules_exist(self) -> None:
        from desktop_backend.articles.command_handlers import delete_selected_articles_handler
        from desktop_backend.articles.payloads import (
            build_article_detail_payload,
            build_article_payload,
            build_articles_payload,
            build_recent_article_payload,
        )
        from desktop_backend.articles.query_handlers import (
            MAX_ARTICLES_PAGE_SIZE,
            get_article_detail_handler,
            get_articles_handler,
            get_recent_articles_handler,
        )

        self.assertEqual(MAX_ARTICLES_PAGE_SIZE, 200)
        self.assertTrue(callable(delete_selected_articles_handler))
        self.assertTrue(callable(build_article_detail_payload))
        self.assertTrue(callable(build_article_payload))
        self.assertTrue(callable(build_articles_payload))
        self.assertTrue(callable(build_recent_article_payload))
        self.assertTrue(callable(get_article_detail_handler))
        self.assertTrue(callable(get_articles_handler))
        self.assertTrue(callable(get_recent_articles_handler))
```

- [ ] **Step 5: Run the article/query regressions**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries tests.test_desktop_backend_structure tests.test_desktop_backend_server -v`

Expected: PASS with article/statistics imports coming only from final modules

- [ ] **Step 6: Search for removed article/schema barrel references**

Run: `rg "desktop_backend\.query_handlers|desktop_backend\.schemas" desktop_backend tests`

Expected: no matches

- [ ] **Step 7: Commit the barrel removal**

```bash
git add desktop_backend/__init__.py desktop_backend/articles desktop_backend/statistics.py tests/test_desktop_backend_queries.py tests/test_desktop_backend_structure.py
git commit -m "refactor: remove legacy article compatibility barrels"
```

### Task 4: Align Active Docs and Run Full Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `tests/test_electron_only_repo.py`
- Test: `tests/test_electron_only_repo.py`

- [ ] **Step 1: Add a failing repo-doc guard for removed shim-module references**

```python
class ElectronOnlyRepoTests(unittest.TestCase):
    def test_active_docs_do_not_reference_removed_shim_modules(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        blocked_snippets = (
            "desktop_backend/task_handlers.py",
            "desktop_backend/tasks/handlers.py",
            "desktop_backend/tasks/registry.py",
            "desktop_backend/tasks/events.py",
            "desktop_backend/tasks/calibration_worker.py",
            "desktop_backend/query_handlers.py",
            "desktop_backend/schemas.py",
        )

        for snippet in blocked_snippets:
            self.assertNotIn(snippet, readme)
            self.assertNotIn(snippet, agents)
            self.assertNotIn(snippet, claude)
```

- [ ] **Step 2: Run the doc guard and confirm it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`

Expected: FAIL because `CLAUDE.md` still mentions `query_handlers.py`, `schemas.py`, and task compatibility wiring

- [ ] **Step 3: Rewrite the active docs to describe the final layout only**

```markdown
<!-- README.md / AGENTS.md / CLAUDE.md -->
- `desktop_backend/statistics.py`: shared statistics payload and `/api/statistics` handler.
- `desktop_backend/task_registry.py`: canonical task registry path.
- `desktop_backend/task_events.py`: canonical task event schema path.
- `desktop_backend/tasks/workflow_handlers.py`: task orchestration entry point used by `desktop_backend/app.py`.
- `desktop_backend/tasks/calibration/`, `desktop_backend/tasks/collection/`, and `desktop_backend/tasks/scraping/`: domain-owned task logic.
```

- [ ] **Step 4: Run the full required verification suite**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure tests.test_desktop_backend_server tests.test_desktop_backend_queries tests.test_desktop_backend_tasks tests.test_electron_only_repo -v`

Expected: PASS

- [ ] **Step 5: Run the desktop checks**

Run: `npm --prefix desktop run typecheck`

Expected: PASS

Run: `npm --prefix desktop run test`

Expected: PASS

- [ ] **Step 6: Confirm the repo no longer references removed shim paths**

Run: `rg "desktop_backend\.task_handlers|desktop_backend\.tasks\.(handlers|registry|events|calibration_worker)|desktop_backend\.query_handlers|desktop_backend\.schemas" desktop_backend tests README.md AGENTS.md CLAUDE.md`

Expected: no matches

- [ ] **Step 7: Commit the doc alignment and final verification pass**

```bash
git add README.md AGENTS.md CLAUDE.md tests/test_electron_only_repo.py
git commit -m "docs: align contributor guidance with final code layout"
```
