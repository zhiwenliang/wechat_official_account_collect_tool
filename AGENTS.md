# Repository Guidelines

## Project Structure

- `main.py`: CLI entry point (calibrate/collect/scrape/stats/retry/index).
- `scraper/`: core automation logic.
  - `calibrator.py`: first-run coordinate calibration for WeChat desktop UI.
  - `link_collector.py`: Stage 1 link collection via `pyautogui` + clipboard.
  - `content_scraper.py`: Stage 2 article scraping via Playwright.
- `storage/`: persistence helpers (`SQLite` + file output).
- `gui/`: optional Tkinter GUI entry (`python -m gui.main`).
- `config/coordinates.json` and `data/`: local runtime state (intentionally gitignored).
  - Outputs land under `data/articles/html/` and `data/articles/markdown/` (plus `data/articles.db`).

## Setup, Run, and Common Commands

```bash
python -m venv .venv && source .venv/bin/activate
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
