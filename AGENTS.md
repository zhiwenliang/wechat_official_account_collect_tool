# Repository Guidelines

## Project Structure

- `desktop/`: Electron + React + TypeScript frontend.
  - `electron/`: main-process and preload code.
  - `src/renderer/`: application pages, components, state, and client API helpers.
- `desktop_backend/`: Python sidecar entrypoint, HTTP server, task registry, query handlers, and import/export handlers.
- `scraper/`: Stage 1 link collection and Stage 2 article scraping internals.
- `services/`: shared calibration, workflow, and data-transfer logic used by the sidecar.
- `storage/`: SQLite access and file export helpers.
- `config/` and `data/`: runtime state (gitignored).

## Environment Management

- This repository is typically run from a Conda environment, not a local `.venv`.
- Prefer reusing the existing Conda environment for this project (for example `wechat-scraper`) instead of creating a new virtualenv unless the user explicitly asks for that.
- Before running Python commands, activate the Conda environment and ensure dependencies are installed there.
- If Python dependencies appear missing, check whether Conda was activated first before assuming the project is misconfigured.

## Setup, Run, and Common Commands

```bash
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper
pip install -r requirements.txt
playwright install chromium

npm --prefix desktop install
npm --prefix desktop run dev
npm --prefix desktop run build
npm --prefix desktop run package:desktop
npm --prefix desktop run typecheck
npm --prefix desktop run test

python -m desktop_backend.app
```

- End users are expected to use the Electron desktop app only.
- Running `python -m desktop_backend.app` directly is a contributor workflow for debugging the sidecar.

## Coding Style & Naming

- Python: 4-space indentation, UTF-8, keep modules small and single-purpose.
- TypeScript/React: follow existing component and state patterns under `desktop/src/renderer/`.
- Naming: `snake_case` for Python functions/vars, `PascalCase` for classes and React components, constants in `UPPER_SNAKE_CASE`.
- Prefer explicit, user-facing logs for long-running automation steps.

## Testing Guidelines

- Python tests use `unittest`; keep coverage focused on sidecar handlers, workflows, storage, and repo-level guardrails.
- Desktop tests use `vitest` under `desktop/src/renderer/**/*.test.tsx`.
- Electron smoke coverage lives under `desktop/tests/e2e/`.
- Avoid adding tests that require real WeChat UI interaction in CI; keep those as manual scripts/docs.

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits, for example `feat: ...`, `refactor: ...`, `chore: ...`, `docs: ...`.
- PRs should describe:
  - which desktop workflow is affected,
  - how to reproduce with Electron and sidecar commands,
  - OS notes when behavior differs between macOS and Windows,
  - screenshots for renderer changes.

## Data, Configuration, and Safety

- Do not commit local artifacts: `config/`, `data/`, databases, or scraped outputs.
- Stage 1 uses `pyautogui` and can move/click the mouse; keep the failsafe behavior intact and document any changes.
- Empty-content articles are tracked by DB content (`status='scraped'` with blank `content_html`), not by a separate status value.
