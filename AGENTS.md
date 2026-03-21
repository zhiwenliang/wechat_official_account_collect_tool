# Repository Guidelines

## Project Structure

- `main.py`: CLI entry point (`calibrate/test/collect/scrape/stats/retry/index`).
- `scraper/`: core automation logic.
  - `calibrator.py`: first-run coordinate calibration for WeChat desktop UI.
  - `link_collector.py`: Stage 1 link collection via `pyautogui` + clipboard.
  - `content_scraper.py`: Stage 2 article scraping via Playwright.
- `services/`: shared workflows for CLI and GUI.
  - `calibration_service.py`: reusable calibration/test flow and config I/O.
  - `workflows.py`: shared collection/scrape/index/retry workflows.
- `storage/`: persistence helpers (`SQLite` + file output).
  - `database.py`: article records, list filtering, retries, empty-content helpers.
  - `file_store.py`: HTML/Markdown export and index generation.
- `gui/`: optional Tkinter GUI entry (`python -m gui.main`).
  - `app.py`: main window, dashboard, article management UI.
  - `worker.py`: background worker threads for long-running operations.
- `config/coordinates.json` and `data/`: local runtime state (intentionally gitignored).
  - Outputs land under `data/articles/html/` and `data/articles/markdown/` (plus `data/articles.db`).

## Environment Management

- This repository is typically run from a Conda environment, not a local `.venv`.
- Prefer reusing the existing Conda environment for this project (for example `wechat-scraper`) instead of creating a new virtualenv unless the user explicitly asks for that.
- Before running project commands, activate the Conda environment and ensure dependencies are installed there.
- If Python dependencies appear missing, check whether Conda was activated first before assuming the project is misconfigured.

## Setup, Run, and Common Commands

```bash
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper
pip install -r requirements.txt
playwright install chromium

python main.py calibrate   # required before Stage 1
python main.py collect     # collect links into the local SQLite DB
python main.py scrape      # fetch article content and write HTML/Markdown backups
python main.py stats       # show pending/scraped/failed counts
python main.py retry       # reset failed -> pending
python main.py index       # regenerate `data/articles/markdown/INDEX.md`
python -m gui.main         # launch GUI (optional)
```

- For day-to-day use, usually only `conda activate wechat-scraper` is needed before running the commands above.

## Coding Style & Naming

- Python: 4-space indentation, UTF-8, keep modules small and single-purpose.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, constants in `UPPER_SNAKE_CASE`.
- Prefer explicit, user-facing logs for long-running automation steps (this tool is interactive by nature).

## Testing Guidelines

- No dedicated test framework is wired up; current checks are runnable scripts:
  - `python main.py test` (calibration sanity checks).
  - `python test_stage1.py` / `python test_stage2.py` (manual, side-effecting).
- Avoid adding “tests” that require real WeChat UI interaction in CI; keep those as scripts/docs.

## Commit & Pull Request Guidelines

- Commit messages follow a Conventional-Commits style seen in history: `feat: ...`, `refactor: ...`, `chore: ...`, `docs: ...` (Chinese or English is fine; be consistent within a PR).
- PRs should describe:
  - which stage is affected (Stage 1 link collection vs Stage 2 scraping),
  - how to reproduce (exact `python main.py ...` commands),
  - OS notes (Windows/macOS behavior differs for window activation),
  - screenshots for GUI changes.

## Data, Configuration, and Safety

- Do not commit local artifacts: `config/coordinates.json`, `data/`, databases, or scraped outputs (already in `.gitignore`).
- Stage 1 uses `pyautogui` and can move/click your mouse; keep the “failsafe” behavior intact and document any changes.
- Empty-content articles are tracked by DB content (`status='scraped'` with blank `content_html`), not by a separate status value.
