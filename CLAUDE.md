# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WeChat Official Account article scraper with two stages:
1. **Stage 1**: Automated link collection via WeChat PC client using pyautogui (GUI automation)
2. **Stage 2**: Content scraping using Playwright to extract article HTML and convert to Markdown

## Commands

### Environment Setup
```bash
# Create and activate conda environment
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### Main Workflow
```bash
# First-time setup: calibrate coordinates for GUI automation
python main.py calibrate

# Test calibration (optional)
python main.py test

# Stage 1: Collect article links (requires manual WeChat window setup)
# Links are saved directly to database
python main.py collect

# Stage 2: Scrape article content
python main.py scrape

# View database statistics
python main.py stats

# Retry failed articles
python main.py retry

# Generate article index
python main.py index

# Launch GUI application
python gui/main.py
```

### Database Queries
```bash
# Check article status distribution
sqlite3 data/articles.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"
```

### Testing
```bash
# Test stage 1 (link collection)
python scripts/manual/stage1_check.py

# Test stage 2 (content scraping)
python scripts/manual/stage2_check.py
```

### GUI Application

The project includes a GUI application built with tkinter:

**GUI Entry Point** (`gui/main.py`)
- Simple entry that launches the GUI application

**GUI Main Window** (`gui/app.py`)
- WeChatScraperGUI class provides:
  - Article list display with status filtering
  - Article preview (HTML/Markdown toggle)
  - Progress tracking during collection/scraping
  - Stop button for interrupting tasks

**Background Workers** (`gui/worker.py`)
- Runs collection and scraping in background threads
- Reports progress back to GUI

**Preview Dialog** (`gui/preview_dialog.py`)
- Displays article content in a scrollable window
- Toggle between HTML and Markdown views

## Architecture

### Two-Stage Pipeline

**Stage 1: Link Collection** (`scraper/link_collector.py`)
- Uses pyautogui to control WeChat PC client
- Requires coordinate calibration (`scraper/calibrator.py`) before first use
- Coordinates stored in `config/coordinates.json`
- Implements intelligent scroll detection (5 consecutive duplicates + refresh confirmation)
- Auto-cleans browser tabs every 30 articles to prevent crashes
- Platform-aware (macOS vs Windows window activation)
- Saves links directly to database

**Stage 2: Content Scraping** (`scraper/content_scraper.py`)
- Uses Playwright (headless=False) to visit article URLs
- Auto-scrolls to load lazy-loaded images
- Parses Chinese date format (e.g., "2026年3月5日 23:39")
- Implements retry mechanism (default: 3 attempts, 10s delay)
- Extracts: title, publish_time, content_html

### Storage Layer

**Database** (`storage/database.py`)
- SQLite at `data/articles.db`
- Schema: `articles(id, title, url UNIQUE, publish_time, scraped_at, status, file_path, content_html, content_markdown)`
- Status values: `pending`, `scraped`, `failed`
- Provides: add, update, get_pending, get_statistics, reset_failed, get_articles_by_status, get_article_detail

**File Store** (`storage/file_store.py`)
- Saves articles in two formats: HTML and Markdown
- Directory structure:
  - `data/articles/html/*.html`
  - `data/articles/markdown/*.md`
- Filename format: `YYYYMMDD_HHMMSS_标题.{html,md}`
- Auto-generates `INDEX.md` with chronological article list (at `data/articles/markdown/INDEX.md`)

### Main Entry Point (`main.py`)

Command dispatcher that orchestrates:
- `calibrate`: Run coordinate calibration wizard
- `test`: Test calibration accuracy
- `collect`: Run link collection (Stage 1) - saves directly to database
- `scrape`: Run content scraping (Stage 2) with auto-retry and index generation
- `stats`: Display database statistics
- `retry`: Reset failed articles to pending status
- `index`: Regenerate article index

### Shared Services

**Config Module** (`config/config_store.py`)
- Loads and saves coordinate configuration
- Default config includes: article_click_area, row_height, scroll_amount, browser button positions, timing settings
- Config stored in `config/coordinates.json`

**Article Formatter** (`services/article_formatter.py`)
- Converts HTML to Markdown using markdownify
- Extracts plain text preview from HTML
- Sanitizes titles for safe filenames
- Builds standalone HTML backup documents

**Workflows** (`services/workflows.py`)
- Shared workflows used by both CLI and GUI
- `run_collection_workflow`: Stage 1 link collection
- `run_scrape_workflow`: Stage 2 content scraping
- `reset_failed_articles`: Reset failed to pending
- `generate_article_index`: Create/update INDEX.md

**Stop Control** (`utils/stop_control.py`)
- `is_stop_requested(stop_checker)`: Check if stop signal received
- `sleep_with_stop(duration, stop_checker)`: Sleep with stop checking

**Escape Listener** (`utils/escape_listener.py`)
- Listens for Escape key to stop long-running tasks
- Works on both CLI (scrape command) and GUI

## Key Implementation Details

### Coordinate Calibration
- Must be run before first link collection
- Records: article row height, scroll amount, button positions (more button, copy link menu, tab controls)
- Window positions must remain fixed after calibration
- Test mode validates all calibrated positions

### Duplicate Detection
- Maintains deque of last 5 links
- On 2-4 consecutive duplicates: warns and continues scrolling
- On 5 consecutive duplicates: attempts to refresh scroll (up then down)
- If still duplicates after refresh: confirms end of list

### Continuous Failure Protection
- Link collector has a max consecutive failures limit (10 attempts)
- If 10 consecutive articles fail to get valid links, auto-stops collection
- Prevents infinite loops when abnormal state is detected

### Remaining Visible Articles
- After scrolling to bottom, processes remaining visible articles without scrolling
- Clicks each visible article to collect links
- Ensures no articles are missed in the current view


### Retry Logic
- Content scraper retries failed articles 3 times with 10s delay
- Database tracks failed articles separately
- `retry` command resets failed → pending for re-scraping

### Image Loading
- Scrolls page incrementally (viewport_height steps)
- 0.5s pause per scroll step to trigger lazy loading
- Ensures all images loaded before HTML extraction

### Time Parsing
- Handles Chinese format: "2026年3月5日 23:39"
- Converts to ISO format for database storage
- Falls back to raw string if parsing fails

## Important Notes

- Stage 1 requires manual WeChat window setup and cannot be interrupted
- Coordinates are platform-specific (macOS vs Windows)
- Playwright runs in non-headless mode for debugging visibility
- Article filenames use publish_time as prefix for chronological sorting
- Database URL field has UNIQUE constraint for automatic deduplication
- Scraping auto-generates index after completion
- Press Escape during scrape to stop the task gracefully
- GUI application runs collection/scraping in background threads with progress tracking
- Database stores both content_html and content_markdown for full article content
