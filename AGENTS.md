# Repository Guidelines

## Project Structure

- `desktop/`: Electron + React + TypeScript frontend.
  - `desktop/electron/`: main-process and preload code.
  - `desktop/src/shared/`: TypeScript shared across Electron layers where appropriate.
  - `desktop/src/renderer/`: application UI (routes, features, shared UI).
    - `desktop/src/renderer/features/`: feature-scoped screens and colocated logic.
    - `desktop/src/renderer/components/`: reusable UI building blocks.
    - `desktop/src/renderer/lib/`: client API helpers, utilities, and integrations (for example task-event streaming).
    - `desktop/src/renderer/state/`: Zustand stores and related UI state.
- `desktop_backend/`: Python sidecar entrypoint, HTTP server, routing, task registry, statistics, and import/export handlers.
  - `desktop_backend/app.py`, `desktop_backend/server.py`, `desktop_backend/server_routes.py`, `desktop_backend/server_runtime.py`, `desktop_backend/import_export_handlers.py`, `desktop_backend/runtime.py`
  - `desktop_backend/task_registry.py`, `desktop_backend/task_events.py`, `desktop_backend/statistics.py`, `desktop_backend/tasks/workflow_handlers.py`
  - `desktop_backend/articles/`: article HTTP/query handling (`query_handlers.py`, `command_handlers.py`, `payloads.py`).
  - `desktop_backend/tasks/calibration/`: calibration task workers and helpers.
  - `desktop_backend/tasks/collection/`: Stage 1 collection task workers and helpers.
  - `desktop_backend/tasks/scraping/`: Stage 2 scraping task workers and helpers.
- `scraper/`: Stage 1 link collection and Stage 2 article scraping internals.
- `services/`: shared calibration, workflow, and data-transfer logic used by the sidecar.
- `storage/`: SQLite access and file export helpers.
- `tests/`: backend/unit coverage plus `tests/test_electron_only_repo.py` for repo guardrails.
- `docs/`: desktop release notes plus historical design and plan docs under `docs/superpowers/`.
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
npm --prefix desktop run e2e

python -m desktop_backend.app
```

- End users are expected to use the Electron desktop app only.
- Running `python -m desktop_backend.app` directly is a contributor workflow for debugging the sidecar.
- Electron resolves the backend via `DESKTOP_BACKEND_EXECUTABLE`, `DESKTOP_BACKEND_PYTHON`, the active Conda env, then packaged sidecar locations.

## Coding Style & Naming

- Python: 4-space indentation, UTF-8, keep modules small and single-purpose.
- TypeScript/React: follow existing component and state patterns under `desktop/src/renderer/`.
- Naming: `snake_case` for Python functions/vars, `PascalCase` for classes and React components, constants in `UPPER_SNAKE_CASE`.
- Prefer explicit, user-facing logs for long-running automation steps.

## Testing Guidelines

- Python tests use `unittest`; keep coverage focused on sidecar handlers, workflows, storage, and repo-level guardrails.
- Prefer `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v` after repo-doc or packaging changes.
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
- If you change packaging or startup behavior, update both `README.md` and `docs/electron-desktop-ui.md` in the same change.

## Learned User Preferences

- For large-scale layout or architecture refactors, prefer phased work (extract layer boundaries, split oversized modules, align features, cleanup) and keep the tree runnable between phases using compatibility re-exports instead of a single rename-everything pass.
- They may ask for an explicit task list and either execute it step-by-step or continue the remaining items automatically once the approach is validated.
- When using a clean git worktree for phased work, prefer committing (or otherwise landing) current changes on the main checkout before creating the worktree.
- When closing out phased work, handle leftover local documentation or editor and tooling state changes in separate commits rather than mixing them into feature-phase merges.

## Learned Workspace Facts

- Desktop Playwright and Electron smoke helpers should resolve the `wechat-scraper` Conda interpreter reliably; using `CONDA_PREFIX` alone can select base Conda when `CONDA_DEFAULT_ENV` is `base` instead of the project environment.
- With `CI` set in the environment, Playwright’s `reuseExistingServer` behavior is typically off, which can surface preview-port conflicts during local E2E runs if a server already holds the configured port.
