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
python -m desktop_backend.app --port 8765

# Start the Electron development app
npm --prefix desktop run dev

# Frontend checks
npm --prefix desktop run typecheck
npm --prefix desktop run test
npm --prefix desktop run build
npm --prefix desktop run package:desktop
```

### Python Tests

```bash
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_server -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries -v
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
- React 18 + TypeScript + Vite
- Renderer pages for dashboard, articles, calibration, collection, and scraping
- Electron preload bridge for backend status and API access

**Python Sidecar** (`desktop_backend/`)
- Stdlib HTTP server plus task registry
- Spawned by `desktop/electron/main.ts`
- Owns workflow execution, DB queries, calibration prompts, and import/export logic

### Shared Backend Modules

- `services/calibration_service.py`: reusable calibration and calibration-test flows
- `services/workflows.py`: collection and scraping workflows with progress/log callbacks
- `services/data_transfer.py`: export/import helpers
- `storage/database.py`: SQLite schema and query helpers
- `storage/file_store.py`: HTML/Markdown persistence plus index generation
- `utils/runtime_env.py`: runtime path resolution for development and packaged runs

## Runtime Notes

- The Electron main process looks for a backend in this order: `DESKTOP_BACKEND_EXECUTABLE`, `DESKTOP_BACKEND_PYTHON`, active Conda environment Python, then packaged sidecar locations.
- Packaged runs should write config and data to platform-specific user state directories, not the repository checkout.
- Stage 1 automation moves the mouse and clicks real UI targets. Preserve safety checks and document any changes.

## Testing Guidance

- Prefer targeted `unittest` modules for backend changes.
- Prefer `vitest` for renderer changes and Playwright for desktop smoke coverage.
- Do not add CI tests that require a real WeChat desktop session.
