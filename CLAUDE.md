# CLAUDE.md

This file provides repository context for coding agents working on the Electron desktop app and its Python sidecar.

## Project Overview

This repository is a WeChat Official Account article scraper with a two-stage automation pipeline and one supported product surface: the Electron desktop application in `desktop/`.

1. **Stage 1**: automated link collection via the WeChat PC client using `pyautogui`
2. **Stage 2**: article scraping with Playwright plus HTML/Markdown export
3. **Desktop product**: Electron renderer and main process in `desktop/`, Python sidecar in `desktop_backend/`

## Commands

### Environment Setup

```bash
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper
pip install -r requirements.txt
playwright install chromium
npm --prefix desktop install
```

### Desktop Application

```bash
# Start the Python sidecar directly when debugging backend behavior
python -m desktop_backend.app

# Start the Electron development app
npm --prefix desktop run dev

# Frontend checks
npm --prefix desktop run typecheck
npm --prefix desktop run test
npm --prefix desktop run build
npm --prefix desktop run package:desktop
npm --prefix desktop run package:desktop:dir  # unpacked build for inspection

# End-to-end smoke tests (builds first, then runs Playwright)
npm --prefix desktop run e2e
```

### Python Tests

```bash
# Core backend tests
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_server -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_tasks -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_import_export -v

# Storage and service tests
conda run -n wechat-scraper python -m unittest tests.test_file_store -v
conda run -n wechat-scraper python -m unittest tests.test_file_store_account_name -v
conda run -n wechat-scraper python -m unittest tests.test_database_account_name -v
conda run -n wechat-scraper python -m unittest tests.test_data_transfer -v
conda run -n wechat-scraper python -m unittest tests.test_workflows -v
conda run -n wechat-scraper python -m unittest tests.test_content_scraper -v

# Repo-level guardrails (run after packaging or doc changes)
conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v
```

## Architecture

### Two-Stage Pipeline

**Stage 1: Link Collection** (`scraper/link_collector.py`)
- Uses `pyautogui` to control the WeChat PC client
- Requires coordinate calibration before collection
- Detects end-of-list conditions via duplicate-link heuristics
- Periodically closes browser tabs to keep the embedded browser stable

**Stage 2: Content Scraping** (`scraper/content_scraper.py`)
- Uses Playwright to fetch article content
- Loads lazy images by scrolling
- Parses Chinese publish-time formats
- Stores HTML and Markdown backups alongside SQLite state

### Electron Desktop App

**Frontend** (`desktop/`)
- React 18 + TypeScript + Vite + Tailwind CSS v4
- Feature screens and colocated logic under `desktop/src/renderer/features/` (dashboard, articles, calibration, collection, scraping workflows).
- Shared UI under `desktop/src/renderer/components/` (for example `ArticlesTable`, `ArticleDetailModal`, `StatisticsCards`, `TaskProgressPanel`, `TaskLogPanel`).
- Client API helpers, utilities, and SSE task streaming under `desktop/src/renderer/lib/` (for example `api.ts`, `task-events.ts`).
- Zustand UI state under `desktop/src/renderer/state/` (for example `app-store.ts`); TanStack React Query for server data.
- Cross-runtime TypeScript shared with the Electron main process under `desktop/src/shared/`.
- Electron preload bridge for backend status and API access
- Unit tests via vitest (`src/**/*.test.tsx`, `electron/**/*.test.ts`)
- E2E smoke tests via Playwright (`tests/e2e/`)

**Python Sidecar** (`desktop_backend/`)
- Stdlib HTTP server (`server.py`) with auto-assigned port (default `0`)
- Spawned by `desktop/electron/main.ts` with retryable startup logic (`electron/retryable-startup.ts`)
- `app.py`: server factory, wires handlers and task registry
- `task_registry.py`: manages running background tasks
- `desktop_backend/articles/`: article-facing HTTP handlers, commands, and article payload builders; `query_handlers.py` and `schemas.py` still re-export from here so existing imports and routing stay stable.
- `desktop_backend/tasks/calibration/`, `desktop_backend/tasks/collection/`, and `desktop_backend/tasks/scraping/`: calibration, collection, and scraping task workers and helpers; `task_handlers.py` and related `tasks/` modules still provide compatibility wiring for the task registry.
- `task_events.py`: typed event and prompt schemas for SSE streaming
- `import_export_handlers.py`: data bundle export and database import
- `runtime.py`: host/port constants and port-availability checks

### Shared Backend Modules

- `services/calibration_service.py`: reusable calibration and calibration-test flows
- `services/workflows.py`: collection and scraping workflows with progress/log callbacks
- `services/data_transfer.py`: export/import helpers
- `storage/database.py`: SQLite schema and query helpers
- `storage/file_store.py`: HTML/Markdown persistence plus index generation
- `utils/runtime_env.py`: runtime path resolution for development and packaged runs
- `utils/stop_control.py`: stop-aware polling helpers for interruptible workflows

### Supporting Directories

- `assets/icons/`: app icons in PNG, ICNS, ICO, and iconset formats
- `config/`: runtime calibration state (gitignored)
- `data/`: scraped output and databases (gitignored)
- `scripts/`: icon generation and manual stage-check helpers
- `docs/`: desktop release notes and historical design/plan docs under `docs/superpowers/`

## Runtime Notes

- The Electron main process looks for a backend in this order: `DESKTOP_BACKEND_EXECUTABLE`, `DESKTOP_BACKEND_PYTHON`, active Conda environment Python, then packaged sidecar locations.
- The sidecar binds to port `0` by default (OS-assigned); Electron reads the actual port from the child process stdout.
- Packaged runs should write config and data to platform-specific user state directories, not the repository checkout.
- Stage 1 automation moves the mouse and clicks real UI targets. Preserve safety checks and document any changes.

## Testing Guidance

- Prefer targeted `unittest` modules for backend changes.
- Prefer `vitest` for renderer changes and Playwright for desktop smoke coverage.
- Run `tests.test_electron_only_repo` after repo-structure or packaging changes.
- Do not add CI tests that require a real WeChat desktop session.
