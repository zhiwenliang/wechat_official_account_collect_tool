# Electron TypeScript Desktop UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Tkinter desktop GUI with an Electron desktop shell and a React + TypeScript renderer while keeping Python as the automation and data backend.

**Architecture:** The implementation introduces a new `desktop/` workspace for Electron and the renderer, plus a Python `desktop_backend/` package that exposes local desktop-facing APIs and task events on top of the existing workflows. Migration stays phased: first prove read-only screens and sidecar startup, then add long-running task flows, then replace calibration, while keeping CLI and Tkinter fallback paths intact.

**Tech Stack:** Python 3.10, existing workflow/storage modules, `unittest`, Electron, React, TypeScript, Vite, Zustand, TanStack Query, WebSocket, local HTTP API, Vitest, Playwright.

---

## File Structure

### New Node/Electron workspace

- `desktop/package.json`
  - Node workspace entry for Electron, Vite, React, tests, and packaging scripts
- `desktop/tsconfig.json`
  - shared TypeScript compiler settings
- `desktop/vite.config.ts`
  - renderer bundling config
- `desktop/electron/main.ts`
  - Electron app bootstrap, BrowserWindow lifecycle, sidecar launch, shutdown handling
- `desktop/electron/preload.ts`
  - restricted bridge exposed to the renderer
- `desktop/src/renderer/main.tsx`
  - renderer entry point
- `desktop/src/renderer/App.tsx`
  - shell layout and route mounting
- `desktop/src/renderer/pages/dashboard/DashboardPage.tsx`
  - dashboard screen
- `desktop/src/renderer/pages/articles/ArticlesPage.tsx`
  - article management screen
- `desktop/src/renderer/pages/collection/CollectionPage.tsx`
  - Stage 1 collection screen
- `desktop/src/renderer/pages/scraping/ScrapingPage.tsx`
  - Stage 2 scraping screen
- `desktop/src/renderer/pages/calibration/CalibrationPage.tsx`
  - calibration screen
- `desktop/src/renderer/lib/api.ts`
  - preload-backed request helpers
- `desktop/src/renderer/lib/task-events.ts`
  - task event subscription helpers
- `desktop/src/renderer/state/app-store.ts`
  - shared UI state that does not belong in server-cache
- `desktop/src/renderer/components/`
  - reusable cards, log viewer, task status panel, article preview pieces

### New Python desktop backend package

- `desktop_backend/__init__.py`
  - package marker
- `desktop_backend/app.py`
  - local API server bootstrap and route registration
- `desktop_backend/server.py`
  - HTTP and WebSocket serving helpers
- `desktop_backend/schemas.py`
  - request and response serialization helpers
- `desktop_backend/task_registry.py`
  - active task bookkeeping, stop routing, and event fan-out
- `desktop_backend/task_events.py`
  - normalized desktop task event builders
- `desktop_backend/query_handlers.py`
  - read-only endpoints backed by `Database` and `FileStore`
- `desktop_backend/task_handlers.py`
  - collection, scraping, calibration, and retry handlers backed by current services
- `desktop_backend/import_export_handlers.py`
  - import/export command endpoints
- `desktop_backend/runtime.py`
  - runtime port selection, path helpers, and sidecar startup metadata

### New tests

- `tests/test_desktop_backend_queries.py`
  - statistics, recent articles, filtered article list behavior
- `tests/test_desktop_backend_server.py`
  - sidecar health check and basic route wiring
- `tests/test_desktop_backend_tasks.py`
  - task lifecycle, progress events, stop semantics
- `tests/test_desktop_backend_import_export.py`
  - import/export endpoint behavior
- `desktop/src/renderer/**/*.test.tsx`
  - focused component and page tests
- `desktop/tests/e2e/desktop-smoke.spec.ts`
  - Electron startup and mocked task smoke test

### Existing files to modify

- `requirements.txt`
  - add Python dependency only if the chosen lightweight local API server is not already available in stdlib shape
- `main.py`
  - keep CLI unchanged unless a dedicated desktop entrypoint is useful
- `README.md`
  - add desktop UI development and startup instructions
- `services/workflows.py`
  - reuse as-is where possible; only adjust if task event hooks need thinner wrappers
- `services/calibration_service.py`
  - expose calibration progress in a backend-friendly way if current callbacks are insufficient
- `storage/database.py`
  - add read helpers only if the desktop screens require data not already available

## Implementation Notes

- Prefer keeping the new frontend isolated under `desktop/` rather than mixing Node files into the Python project root.
- Prefer a Python standard-library HTTP server plus a small WebSocket dependency only if necessary; do not introduce a large Python web framework unless the standard-library path proves too limiting.
- Treat the current Tkinter GUI as fallback during the migration. Do not remove `gui/` in this plan.
- The first end-to-end milestone is successful sidecar startup plus Dashboard and Article Management rendered from real backend data.

### Task 1: Scaffold the Desktop Workspace

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/tsconfig.json`
- Create: `desktop/vite.config.ts`
- Create: `desktop/electron/main.ts`
- Create: `desktop/electron/preload.ts`
- Create: `desktop/src/renderer/main.tsx`
- Create: `desktop/src/renderer/App.tsx`
- Create: `desktop/src/renderer/styles.css`
- Modify: `README.md`

- [ ] **Step 1: Write the failing workspace smoke check**

Add a minimal renderer smoke test file such as `desktop/src/renderer/App.test.tsx` that imports `App` and expects a shell heading like `微信公众号文章采集工具`.

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App shell", () => {
  it("renders the desktop shell heading", () => {
    render(<App />);
    expect(screen.getByText("微信公众号文章采集工具")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm --prefix desktop test -- App.test.tsx`
Expected: FAIL because the Node workspace and renderer files do not exist yet.

- [ ] **Step 3: Create the desktop workspace and app shell**

Create the Electron and Vite workspace with scripts for:
- `dev`
- `build`
- `test`
- `e2e`

Keep the first `App` minimal: navigation shell only, no business logic.

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm --prefix desktop test -- App.test.tsx`
Expected: PASS

- [ ] **Step 5: Update desktop setup documentation**

Document:
- Node version expectation
- `npm --prefix desktop install`
- `npm --prefix desktop run dev`
- relationship between Electron and the Python sidecar

- [ ] **Step 6: Commit**

```bash
git add README.md desktop
git commit -m "feat: scaffold electron desktop workspace"
```

### Task 2: Lock Query API Behavior With Python Tests

**Files:**
- Create: `tests/test_desktop_backend_queries.py`
- Create: `desktop_backend/__init__.py`
- Create: `desktop_backend/schemas.py`
- Create: `desktop_backend/query_handlers.py`

- [ ] **Step 1: Write failing tests for read-only backend queries**

Cover:
- statistics payload shape
- recent articles payload ordering
- article list filtering, search, and pagination mapping

Example:

```python
def test_get_statistics_returns_expected_counts():
    db = Database(temp_db_path)
    db.add_article("https://example.com/1")

    result = get_statistics_handler(db=db)

    assert result["total"] == 1
    assert result["pending"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_queries -v`
Expected: FAIL because `desktop_backend.query_handlers` does not exist yet.

- [ ] **Step 3: Implement minimal query handlers**

Add pure functions for:
- `get_statistics_handler`
- `get_recent_articles_handler`
- `get_articles_handler`

Keep them independent from HTTP transport so they are easy to test directly.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_queries -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop_backend/__init__.py desktop_backend/query_handlers.py desktop_backend/schemas.py tests/test_desktop_backend_queries.py
git commit -m "feat: add desktop backend query handlers"
```

### Task 3: Build the Python Sidecar Server Skeleton

**Files:**
- Create: `desktop_backend/app.py`
- Create: `desktop_backend/server.py`
- Create: `desktop_backend/runtime.py`
- Create: `tests/test_desktop_backend_server.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing sidecar startup test**

Add a test that boots the backend in-process, requests `/health`, and verifies a JSON payload like:

```python
{"status": "ok", "service": "desktop-backend"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_server -v`
Expected: FAIL because the sidecar server entrypoint does not exist yet.

- [ ] **Step 3: Implement the minimal server skeleton**

Implement:
- runtime port selection
- `/health`
- query route registration for statistics and article endpoints
- JSON serialization helpers

Keep the transport thin and route handlers delegated to `query_handlers.py`.

- [ ] **Step 4: Run backend tests**

Run:
- `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_queries -v`
- `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_server -v`

Expected: PASS

- [ ] **Step 5: Document how to run the sidecar directly during development**

Add a section such as:

```bash
conda activate wechat-scraper
python -m desktop_backend.app
```

- [ ] **Step 6: Commit**

```bash
git add README.md desktop_backend/app.py desktop_backend/runtime.py desktop_backend/server.py tests/test_desktop_backend_server.py
git commit -m "feat: add desktop backend server skeleton"
```

### Task 4: Add Task Registry and Event Stream Primitives

**Files:**
- Create: `desktop_backend/task_events.py`
- Create: `desktop_backend/task_registry.py`
- Create: `tests/test_desktop_backend_tasks.py`

- [ ] **Step 1: Write failing tests for task lifecycle behavior**

Cover:
- task registration creates a task id
- progress and log events are buffered or broadcast in order
- stop requests mark the task as stopping
- completion clears active state

Example:

```python
def test_task_registry_marks_task_stopping():
    registry = TaskRegistry()
    task_id = registry.start_task("collection")

    registry.request_stop(task_id)

    assert registry.should_stop(task_id) is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
Expected: FAIL because the task registry does not exist yet.

- [ ] **Step 3: Implement the minimal registry and event builders**

Implement:
- `TaskRegistry`
- normalized event payload builders for `started`, `log`, `progress`, `status`, `completed`, `error`, `stopped`, `cancelled`

Do not couple this layer to collection or scraping yet.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop_backend/task_events.py desktop_backend/task_registry.py tests/test_desktop_backend_tasks.py
git commit -m "feat: add desktop task registry primitives"
```

### Task 5: Expose Collection and Scraping Tasks Through the Backend

**Files:**
- Create: `desktop_backend/task_handlers.py`
- Modify: `desktop_backend/app.py`
- Modify: `desktop_backend/task_registry.py`
- Modify: `services/workflows.py`

- [ ] **Step 1: Write failing tests for task-backed workflow execution**

Cover:
- starting a collection task emits `started`
- workflow logs are surfaced as `log` events
- progress callbacks become `progress` events
- stop requests are honored through the workflow stop checker

Use a fake collector and fake scraper in tests instead of real UI automation.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
Expected: FAIL because collection and scraping task handlers are not implemented.

- [ ] **Step 3: Implement collection and scraping task adapters**

Wrap:
- `run_collection_workflow`
- `run_scrape_workflow`

Translate their existing `log` and `progress` callbacks into task events through `TaskRegistry`.

- [ ] **Step 4: Add stop-aware route handlers**

Add endpoints similar to:
- `POST /tasks/collection`
- `POST /tasks/scrape`
- `POST /tasks/{task_id}/stop`

- [ ] **Step 5: Run the tests to verify they pass**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desktop_backend/app.py desktop_backend/task_handlers.py desktop_backend/task_registry.py services/workflows.py tests/test_desktop_backend_tasks.py
git commit -m "feat: expose collection and scraping tasks to desktop backend"
```

### Task 6: Add Import/Export and Article Action Endpoints

**Files:**
- Create: `desktop_backend/import_export_handlers.py`
- Modify: `desktop_backend/app.py`
- Modify: `desktop_backend/query_handlers.py`
- Create: `tests/test_desktop_backend_import_export.py`

- [ ] **Step 1: Write failing tests for desktop command endpoints**

Cover:
- retry failed articles
- retry empty-content articles
- delete selected articles
- export data bundle
- import database with existing backup behavior

- [ ] **Step 2: Run the tests to verify they fail**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_import_export -v`
Expected: FAIL because the endpoint handlers do not exist yet.

- [ ] **Step 3: Implement minimal command handlers**

Reuse existing logic from:
- `services.data_transfer`
- `storage.database.Database`

Keep the HTTP routes thin and the business behavior in callable handlers.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_import_export -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop_backend/app.py desktop_backend/import_export_handlers.py desktop_backend/query_handlers.py tests/test_desktop_backend_import_export.py
git commit -m "feat: add desktop import export and article action endpoints"
```

### Task 7: Launch the Python Sidecar From Electron

**Files:**
- Modify: `desktop/electron/main.ts`
- Modify: `desktop/electron/preload.ts`
- Create: `desktop/src/renderer/lib/api.ts`
- Create: `desktop/src/renderer/lib/task-events.ts`
- Create: `desktop/tests/e2e/desktop-smoke.spec.ts`

- [ ] **Step 1: Write the failing Electron smoke test**

Cover:
- Electron starts
- sidecar launch is attempted
- renderer can call the health endpoint through preload

Example Playwright expectation:

```ts
await expect(page.getByText("连接状态: 已连接")).toBeVisible();
```

- [ ] **Step 2: Run the smoke test to verify it fails**

Run: `npm --prefix desktop run e2e -- desktop-smoke.spec.ts`
Expected: FAIL because Electron does not launch the sidecar or expose a preload API yet.

- [ ] **Step 3: Implement sidecar process lifecycle in Electron**

Implement:
- spawn Python sidecar on app startup
- wait for health readiness
- shut down sidecar on app exit
- surface startup failures in a desktop-safe way

- [ ] **Step 4: Implement the preload bridge**

Expose a narrow API like:

```ts
contextBridge.exposeInMainWorld("desktopApi", {
  getHealth: () => invokeHealthCheck(),
  getStatistics: () => request("/stats"),
  subscribeTaskEvents: (listener) => subscribe(listener),
});
```

- [ ] **Step 5: Run the smoke test to verify it passes**

Run: `npm --prefix desktop run e2e -- desktop-smoke.spec.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add desktop/electron/main.ts desktop/electron/preload.ts desktop/src/renderer/lib/api.ts desktop/src/renderer/lib/task-events.ts desktop/tests/e2e/desktop-smoke.spec.ts
git commit -m "feat: wire electron to python sidecar"
```

### Task 8: Ship Dashboard and Article Management

**Files:**
- Create: `desktop/src/renderer/pages/dashboard/DashboardPage.tsx`
- Create: `desktop/src/renderer/pages/articles/ArticlesPage.tsx`
- Create: `desktop/src/renderer/components/StatisticsCards.tsx`
- Create: `desktop/src/renderer/components/ArticlesTable.tsx`
- Create: `desktop/src/renderer/state/app-store.ts`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Write failing renderer tests for read-only screens**

Cover:
- dashboard renders statistics from API data
- recent articles render in descending time order
- article list search and filter controls call the API with expected parameters

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix desktop test -- DashboardPage ArticlesPage`
Expected: FAIL because the pages and API hooks do not exist yet.

- [ ] **Step 3: Implement dashboard and article pages**

Use:
- TanStack Query for backend-backed data
- local state only for transient UI controls

Keep article preview read-only in this task.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm --prefix desktop test -- DashboardPage ArticlesPage`
Expected: PASS

- [ ] **Step 5: Manual smoke check against the real backend**

Run:
- `conda activate wechat-scraper`
- `npm --prefix desktop run dev`

Verify:
- stats cards load
- recent articles render
- article search, filters, and pagination work on real data

- [ ] **Step 6: Commit**

```bash
git add desktop/src/renderer/App.tsx desktop/src/renderer/components desktop/src/renderer/pages/articles desktop/src/renderer/pages/dashboard desktop/src/renderer/state/app-store.ts
git commit -m "feat: add dashboard and article management pages"
```

### Task 9: Ship Collection and Scraping Task Screens

**Files:**
- Create: `desktop/src/renderer/pages/collection/CollectionPage.tsx`
- Create: `desktop/src/renderer/pages/scraping/ScrapingPage.tsx`
- Create: `desktop/src/renderer/components/TaskLogPanel.tsx`
- Create: `desktop/src/renderer/components/TaskProgressPanel.tsx`
- Modify: `desktop/src/renderer/lib/api.ts`
- Modify: `desktop/src/renderer/lib/task-events.ts`

- [ ] **Step 1: Write failing renderer tests for task screens**

Cover:
- start button triggers collection or scraping command
- event stream updates progress and log panels
- stop button disables once a stop request is in flight

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm --prefix desktop test -- CollectionPage ScrapingPage`
Expected: FAIL because task screen components do not exist yet.

- [ ] **Step 3: Implement collection and scraping pages**

Render:
- preparation guidance
- current task status
- progress meter
- append-only log stream
- stop control

Do not add extra workflow features not already present in the Tkinter app.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm --prefix desktop test -- CollectionPage ScrapingPage`
Expected: PASS

- [ ] **Step 5: Manual desktop smoke check**

Verify in the Electron app:
- start collection creates a task
- logs stream live
- stop halts the task cleanly
- start scraping reflects success and failure counts

- [ ] **Step 6: Commit**

```bash
git add desktop/src/renderer/components/TaskLogPanel.tsx desktop/src/renderer/components/TaskProgressPanel.tsx desktop/src/renderer/lib/api.ts desktop/src/renderer/lib/task-events.ts desktop/src/renderer/pages/collection desktop/src/renderer/pages/scraping
git commit -m "feat: add collection and scraping task pages"
```

### Task 10: Replace the Calibration Screen

**Files:**
- Create: `desktop/src/renderer/pages/calibration/CalibrationPage.tsx`
- Modify: `desktop_backend/task_handlers.py`
- Modify: `services/calibration_service.py`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Write failing tests for calibration task state transitions**

Cover:
- backend emits step prompts in order
- renderer shows the active prompt
- confirmation and cancellation map to backend requests correctly

- [ ] **Step 2: Run the tests to verify they fail**

Run:
- `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
- `npm --prefix desktop test -- CalibrationPage`

Expected: FAIL because calibration task prompts are not modeled for the desktop API yet.

- [ ] **Step 3: Adapt calibration flow for desktop-friendly prompts**

Do not rewrite calibration logic. Instead, add an adapter layer that turns the existing callback-driven flow into task events such as:
- `awaiting_position`
- `awaiting_integer`
- `countdown`
- `completed`

- [ ] **Step 4: Implement the renderer page**

Render:
- current calibration step
- user instructions
- action buttons for record, continue, cancel, and test

- [ ] **Step 5: Run tests to verify they pass**

Run:
- `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_desktop_backend_tasks -v`
- `npm --prefix desktop test -- CalibrationPage`

Expected: PASS

- [ ] **Step 6: Manual validation against the real WeChat desktop app**

Run:
- `conda activate wechat-scraper`
- `npm --prefix desktop run dev`

Verify the full calibration and test-calibration flows complete without Tkinter.

- [ ] **Step 7: Commit**

```bash
git add desktop/src/renderer/App.tsx desktop/src/renderer/pages/calibration desktop_backend/task_handlers.py services/calibration_service.py tests/test_desktop_backend_tasks.py
git commit -m "feat: add desktop calibration flow"
```

### Task 11: Packaging, Fallbacks, and Release Documentation

**Files:**
- Modify: `desktop/package.json`
- Modify: `desktop/electron/main.ts`
- Modify: `README.md`
- Create: `docs/electron-desktop-ui.md`

- [ ] **Step 1: Write the failing packaging checklist**

Create a release checklist covering:
- packaged Electron app starts the Python sidecar
- sidecar finds runtime paths correctly
- startup failure is user-visible
- Tkinter fallback remains available during migration

- [ ] **Step 2: Implement packaging scripts and fallback notes**

Add:
- build script for the Electron app
- packaged sidecar startup configuration
- clear fallback instructions for `python -m gui.main`

- [ ] **Step 3: Run release smoke checks**

Run:
- `npm --prefix desktop run build`
- `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest`

Expected:
- Electron bundle builds successfully
- Python regression suite still passes

- [ ] **Step 4: Update release documentation**

Document:
- developer startup
- packaged app behavior
- current known limitations during the migration window

- [ ] **Step 5: Commit**

```bash
git add README.md docs/electron-desktop-ui.md desktop/package.json desktop/electron/main.ts
git commit -m "docs: add desktop packaging and migration notes"
```
