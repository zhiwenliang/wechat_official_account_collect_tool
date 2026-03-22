# Electron TypeScript Desktop UI Design

**Feature:** replace the Tkinter desktop GUI with a modern Electron desktop shell and a React + TypeScript renderer while keeping the existing Python automation core.

## Scope

- Build a new local desktop UI for the existing scraper application.
- Keep Python as the source of truth for:
  - calibration
  - link collection
  - content scraping
  - SQLite access
  - import/export workflows
- Introduce Electron as the desktop shell.
- Introduce a TypeScript frontend for all interactive screens.
- Support a staged migration where Tkinter remains available until the new desktop UI covers the required workflows.

## Non-Goals

- Do not rewrite Stage 1 and Stage 2 scraper logic in TypeScript.
- Do not move SQLite access into the renderer process.
- Do not remove the CLI entry points.
- Do not require the first shipped version to fully replace the calibration workflow.

## Current State

- The current desktop UI is concentrated in `gui/app.py` and mixes page layout, user interactions, task orchestration, and Tkinter-specific state.
- Core workflows already live outside Tkinter:
  - `services/workflows.py`
  - `services/calibration_service.py`
  - `storage/database.py`
  - `storage/file_store.py`
- Background work is currently exposed to the GUI via thread workers in `gui/worker.py`.

This means the highest-value refactor is replacing the UI shell and interaction layer, not rewriting the business logic.

## Target Architecture

The application will use three layers:

1. `Electron main`
   - owns the application window, menus, dialog bridges, and Python process lifecycle
   - exposes a restricted preload API to the renderer
2. `React + TypeScript renderer`
   - renders all screens
   - manages client-side view state and task subscriptions
   - never accesses Node or SQLite directly
3. `Python desktop backend`
   - runs as a sidecar process
   - owns scraper workflows, calibration flows, runtime paths, database operations, and file export/import

Electron remains a shell and broker. Python remains the business backend.

## Frontend Modules

The renderer should be split into focused screens that mirror the current user workflows:

- Dashboard
  - statistics cards
  - recent articles
  - next-step guidance
- Calibration
  - step-by-step item flow
  - status and validation messages
  - test-calibration entry points
- Link Collection
  - preparation checklist
  - start/stop controls
  - progress display
  - real-time logs
- Content Scraping
  - pending and empty-content counts
  - start/stop controls
  - success/failure summary
  - real-time logs
- Article Management
  - filters, search, pagination
  - batch actions
  - article preview
  - import/export entry points

## Backend Interface

The Python sidecar should expose a local desktop-facing API with two categories of operations.

### Query and command endpoints

- get statistics
- get recent articles
- query article list
- retry failed articles
- retry empty-content articles
- delete selected articles
- export data bundle
- import database
- start collection task
- start scraping task
- start calibration task
- start calibration test
- request task stop

### Task event stream

Long-running operations should publish structured task events:

- `started`
- `log`
- `progress`
- `status`
- `completed`
- `error`
- `stopped`
- `cancelled`

The renderer listens to these events and updates UI state without knowing Tkinter-era worker details.

## IPC Strategy

Use a local API boundary instead of pushing scraper logic into Electron IPC handlers.

- Renderer calls a preload API.
- Preload forwards requests to a local Python service.
- Long-running task updates flow back through a streaming channel.

Recommended development shape:

- request/response: local HTTP
- streaming events: WebSocket

This keeps the desktop shell thin and avoids creating a second backend inside Electron main.

## Migration Plan

Migrate in phases instead of attempting a full cutover.

### Phase 1

- Bootstrap Electron, preload bridge, Python sidecar startup, and React app shell.
- Implement Dashboard and Article Management.
- Reuse existing database and file-store logic through Python APIs.

### Phase 2

- Implement Link Collection and Content Scraping pages.
- Introduce task lifecycle handling, real-time logs, progress bars, and stop controls.

### Phase 3

- Implement the Calibration page with explicit step prompts and result handling.
- Replace Tkinter-only coordination patterns with backend task events that the renderer can consume.

### Phase 4

- Validate parity for required workflows.
- Keep Tkinter as fallback until the Electron UI is operational for normal day-to-day use.
- Retire Tkinter only after feature parity is confirmed.

## Packaging

- Package Electron with a bundled Python runtime or a project-owned Python distribution.
- Keep runtime path resolution in Python so source runs and packaged runs share one path model.
- Treat Windows packaging as the primary target for the first release.

## Error Handling

- If the Python sidecar fails to start, the Electron shell must show a startup error and stop cleanly.
- If a task crashes, the renderer should show terminal status and preserve recent logs.
- If the renderer closes while a task is running, Electron should request task stop before process shutdown.
- Destructive actions such as database import must keep an explicit confirmation step.

## Testing and Verification

- Keep existing Python tests for workflow and storage behavior.
- Add focused tests for the new Python desktop-facing API.
- Add frontend component tests for key state transitions.
- Add one end-to-end desktop smoke test for:
  - app startup
  - dashboard statistics render
  - article list query
  - launch and stop of a mocked long-running task

## Open Decisions Resolved

- Desktop shell: Electron
- Frontend stack: React + TypeScript
- Backend ownership: Python remains authoritative for automation and data
- Migration strategy: phased rollout, not big-bang replacement

## Implementation Notes

- The first deliverable does not need to replace calibration immediately.
- The first milestone should prove the new architecture with read-heavy and low-risk screens before moving to automation-heavy flows.
- Existing CLI commands remain supported throughout the migration.
