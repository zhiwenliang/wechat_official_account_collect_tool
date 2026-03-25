# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WeChat Official Account article scraper with a two-stage pipeline and three UI surfaces:

1. **Stage 1**: Automated link collection via WeChat PC client using pyautogui (GUI automation)
2. **Stage 2**: Content scraping using Playwright to extract article HTML and convert to Markdown
3. **Three UIs**: CLI (`main.py`), legacy tkinter GUI (`gui/main.py`), and Electron desktop app (`desktop/`)

## Commands

### Environment Setup
```bash
# Create and activate conda environment
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper

# Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# Install desktop frontend dependencies
cd desktop && npm install && cd ..
```

### Main CLI Workflow
```bash
# First-time setup: calibrate coordinates for GUI automation
python main.py calibrate

# Test calibration (optional)
python main.py test

# Stage 1: Collect article links (requires manual WeChat window setup)
python main.py collect

# Stage 2: Scrape article content
python main.py scrape

# View database statistics
python main.py stats

# Retry failed articles
python main.py retry

# Generate article index
python main.py index

# Export data bundle (database + article files as zip)
python main.py export-data <zip_path>

# Import external database file
python main.py import-db <db_path>
```

### Desktop Application (Electron + Python sidecar)
```bash
# Start desktop backend sidecar manually (for development)
python -m desktop_backend.app --port 8765

# Start Electron frontend in dev mode
cd desktop && npm run dev

# Run frontend unit tests (vitest)
cd desktop && npm test

# Run frontend E2E tests (Playwright)
cd desktop && npm run e2e

# Type-check frontend
cd desktop && npm run typecheck

# Build desktop frontend
cd desktop && npm run build

# Package as standalone desktop app
cd desktop && npm run package:desktop
```

### Legacy tkinter GUI
```bash
python gui/main.py
```

### Python Tests
```bash
# Run all Python tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_desktop_backend_server.py
```

### Database Queries
```bash
sqlite3 data/articles.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"
```

### CI / Packaging
```bash
# Package GUI executable (PyInstaller)
python scripts/package_app.py --target gui --archive
```

## Architecture

### Two-Stage Pipeline

**Stage 1: Link Collection** (`scraper/link_collector.py`)
- Uses pyautogui to control WeChat PC client
- Requires coordinate calibration before first use
- Implements intelligent scroll detection (5 consecutive duplicates + refresh confirmation)
- Auto-cleans browser tabs every 30 articles to prevent crashes
- Platform-aware (macOS vs Windows window activation)
- Saves links directly to database

**Stage 2: Content Scraping** (`scraper/content_scraper.py`)
- Uses Playwright (headless=False) to visit article URLs
- Auto-scrolls to load lazy-loaded images
- Parses Chinese date format (e.g., "2026年3月5日 23:39")
- Implements retry mechanism (default: 3 attempts, 10s delay)
- Extracts: title, account_name, publish_time, content_html

### Desktop Application (Electron + Python Sidecar)

The desktop app is a two-process architecture:

**Electron Frontend** (`desktop/`)
- React 18 + TypeScript + Vite
- State management: Zustand (`desktop/src/renderer/state/app-store.ts`)
- Data fetching: TanStack React Query
- Pages: Dashboard, Articles, Calibration, Collection, Scraping
- Communicates with Python backend via HTTP REST API
- IPC bridge: Electron preload exposes `window.desktop.getBackendStatus()`

**Python Backend Sidecar** (`desktop_backend/`)
- Pure stdlib HTTP server (`http.server.ThreadingHTTPServer`) — no Flask/FastAPI
- Spawned as child process by Electron main process (`PythonSidecarController`)
- Dynamic port allocation: reserves ephemeral port, passes via env `DESKTOP_BACKEND_PORT`
- Entry point: `desktop_backend/app.py` → `create_server()` → `DesktopBackendServer`

**Backend API Routes:**
- `GET /health` — health check
- `GET /api/statistics` — article statistics
- `GET /api/recent-articles?limit=N` — recent articles
- `GET /api/articles?status=&search=&page=&page_size=&sort_column=&descending=` — paginated article list
- `POST /api/articles/retry-failed` — reset failed → pending
- `POST /api/articles/retry-empty-content` — reset empty-content → pending
- `POST /api/articles/delete` — delete articles by IDs (body: `{article_ids: []}`)
- `POST /api/data/export` — export data bundle (body: `{output_path}`)
- `POST /api/data/import` — import database file (body: `{source_db_path}`)
- `POST /tasks/collection` — start collection task → returns `{task_id}`
- `POST /tasks/scrape` — start scrape task → returns `{task_id}`
- `POST /tasks/calibration` — start calibration task (body: `{action}`)
- `GET /tasks/{task_id}` — get task snapshot (events, status, prompt)
- `POST /tasks/{task_id}/stop` — request task stop
- `POST /tasks/{task_id}/respond` — submit response to calibration prompt

**Task System** (`desktop_backend/task_registry.py`, `task_handlers.py`, `task_events.py`):
- `TaskRegistry`: thread-safe task lifecycle tracker with event log
- Tasks emit typed events: `started`, `log`, `progress`, `status`, `prompt`, `completed`, `error`, `stopped`, `cancelled`
- `TaskPrompt`: interactive prompts for calibration (kinds: `position`, `ack`, `integer`, `confirm`)
- `WorkflowTaskHandlers`: factory pattern with DI for collector/scraper/db/filestore

**Backend Schemas** (`desktop_backend/schemas.py`):
- TypedDict payloads: `StatisticsPayload`, `ArticlePayload`, `ArticlesPayload`, `RecentArticlePayload`
- Builder functions normalize raw DB tuples into JSON-safe dicts

### Shared Services

**Calibration Service** (`services/calibration_service.py`)
- Unified calibration logic for CLI, tkinter GUI, and desktop app
- Desktop flow uses per-item actions: `article_click_area`, `scroll_amount`, `visible_articles`, `more_button`, `copy_link_menu`, `tab_management`, `test`
- Protocol-based callbacks: `DesktopRequestPositionFn`, `DesktopRequestAckFn`, `DesktopRequestIntegerFn`, `DesktopRequestConfirmFn`
- Raises `CalibrationCancelled` on user cancel or stop signal

**Workflows** (`services/workflows.py`)
- `run_collection_workflow()`: Stage 1 link collection with progress callbacks
- `run_scrape_workflow()`: Stage 2 content scraping with progress callbacks
- `reset_failed_articles()`, `reset_empty_content_articles()`, `generate_article_index()`
- Returns `CollectionResult` or `ScrapeResult` dataclasses

**Data Transfer** (`services/data_transfer.py`)
- `export_data_bundle()`: exports DB + article files as zip archive
- `import_database_file()`: imports external .db with auto-backup of existing

**Article Formatter** (in `storage/file_store.py`)
- Converts HTML to Markdown using markdownify
- Sanitizes titles for safe filenames
- Builds standalone HTML backup documents
- Generates INDEX.md with chronological article list

### Storage Layer

**Database** (`storage/database.py`)
- SQLite at `data/articles.db` (via `resolve_runtime_path`)
- Schema: `articles(id, title, account_name, url UNIQUE, publish_time, scraped_at, status, file_path, content_html, content_markdown)`
- Status values: `pending`, `scraped`, `failed`
- Computed status: `empty_content` (scraped but content_html is empty)
- Auto-migration: adds missing columns on startup
- Indexes: `idx_articles_status_id`, `idx_articles_publish_time`
- Paginated queries with search, sort, and filter support

**File Store** (`storage/file_store.py`)
- Saves articles in two formats: HTML and Markdown
- Directory structure: `data/articles/html/*.html`, `data/articles/markdown/*.md`
- Filename format: `YYYYMMDD_HHMMSS_标题.{html,md}`
- `delete_article_files()`: removes article backups within managed tree
- `generate_index()`: creates INDEX.md at `data/articles/markdown/INDEX.md`

**Runtime Environment** (`utils/runtime_env.py`)
- `resolve_runtime_path()`: maps repo-relative paths to writable locations
- When frozen (PyInstaller): uses platform-specific app data dirs (`~/Library/Application Support/WeChatScraper` on macOS)
- When development: resolves to repo root
- `configure_runtime_environment()`: locates bundled Playwright browsers

### Shared Config

**Coordinate Config** (`config/coordinates.json`)
- Loaded/saved via `services/calibration_service.py`
- Structure: `windows.article_list` (click area, row height, scroll, visible count) + `windows.browser` (more button, copy link menu, tabs) + `timing` + `collection`

**Stop Control** (`utils/stop_control.py`)
- `is_stop_requested(stop_checker)`: check if stop signal received
- `sleep_with_stop(duration, stop_checker)`: sleep with periodic stop checking

**Escape Listener** (`utils/escape_listener.py`)
- Listens for Escape key to stop long-running CLI tasks

### Legacy tkinter GUI (`gui/`)

- Entry: `gui/main.py` → `gui/app.py` (`WeChatScraperGUI`)
- Tabs: Dashboard, Link Collection, Content Scraping, Articles, Calibration
- Background workers: `gui/worker.py`
- Preview dialog: `gui/preview_dialog.py`
- Styling constants: `gui/styles.py`

### Desktop Frontend (`desktop/src/renderer/`)

- `App.tsx`: main shell with backend status polling and page sections
- `pages/dashboard/DashboardPage.tsx`: statistics cards + recent articles
- `pages/articles/ArticlesPage.tsx`: paginated article table with search/filter
- `pages/calibration/CalibrationPage.tsx`: per-item calibration workflow
- `pages/collection/CollectionPage.tsx`: link collection with live progress
- `pages/scraping/ScrapingPage.tsx`: content scraping with live progress
- `components/`: `StatisticsCards`, `ArticlesTable`, `TaskProgressPanel`, `TaskLogPanel`
- `lib/api.ts`: API client (getStatistics, getArticles, startCollectionTask, etc.)
- `lib/task-events.ts`: TypeScript types for backend task events and status
- `state/app-store.ts`: Zustand store

### Desktop Electron Main Process (`desktop/electron/`)

- `main.ts`: window creation, `PythonSidecarController` lifecycle
- `preload.ts`: IPC bridge exposing `window.desktop` API
- Python command resolution: checks `DESKTOP_BACKEND_PYTHON`, `CONDA_PREFIX`, or defaults
- Packaged mode: looks for frozen sidecar in resources directory

## Key Implementation Details

### Coordinate Calibration
- Must be run before first link collection
- Records: article row height, scroll amount, button positions (more button, copy link menu, tab controls)
- Window positions must remain fixed after calibration
- Test mode validates all calibrated positions
- Desktop app supports per-item recalibration (individual actions)

### Duplicate Detection
- Maintains deque of last 5 links
- On 2-4 consecutive duplicates: warns and continues scrolling
- On 5 consecutive duplicates: attempts to refresh scroll (up then down)
- If still duplicates after refresh: confirms end of list

### Continuous Failure Protection
- Link collector has a max consecutive failures limit (10 attempts)
- If 10 consecutive articles fail to get valid links, auto-stops collection

### Remaining Visible Articles
- After scrolling to bottom, processes remaining visible articles without scrolling
- Uses row_height to calculate click positions for each visible row

### Retry Logic
- Content scraper retries failed articles 3 times with 10s delay
- Database tracks failed articles separately
- `retry` command resets failed → pending for re-scraping
- `retry-empty-content` resets scraped-but-empty → pending

### Image Loading
- Scrolls page incrementally (viewport_height steps)
- 0.5s pause per scroll step to trigger lazy loading

### Time Parsing
- Handles Chinese format: "2026年3月5日 23:39"
- Converts to ISO format for database storage

## Important Notes

- Stage 1 requires manual WeChat window setup and cannot be interrupted mid-click
- Coordinates are platform-specific (macOS vs Windows)
- Playwright runs in non-headless mode for debugging visibility
- Database URL field has UNIQUE constraint for automatic deduplication
- Press Escape during CLI scrape to stop the task gracefully
- Desktop app tasks are stoppable via REST API (`POST /tasks/{id}/stop`)
- Database stores both content_html and content_markdown
- Desktop backend uses no external web framework — pure stdlib `http.server`
- Desktop backend port is dynamically allocated (ephemeral port 0)
- `resolve_runtime_path()` ensures frozen executables use platform app-data dirs
- CI workflow packages the tkinter GUI as standalone executable via PyInstaller
- Desktop Electron packaging uses electron-builder with asar
