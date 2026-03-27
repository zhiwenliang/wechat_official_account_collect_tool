# Codebase File Structure Optimization Design

**Feature:** reorganize the repository into clearer runtime and domain boundaries so large files can be split safely and future work lands in predictable locations.

## Scope

- Define a long-term target structure for the repository.
- Optimize file organization for the supported Electron desktop product and Python sidecar architecture.
- Reduce mixed-responsibility modules by introducing clearer package boundaries before broad file splitting.
- Establish a staged migration path that keeps the repo runnable and testable throughout the refactor.

## Non-Goals

- Do not redesign product behavior or user workflows.
- Do not rewrite Python automation logic into TypeScript.
- Do not replace the Electron + sidecar architecture with a different deployment model.
- Do not perform a big-bang file move where the repo is broken until all imports are repaired.

## Current State

- The repository already has reasonable top-level separation:
  - `desktop/` for Electron + React
  - `desktop_backend/` for the Python sidecar
  - `services/` for shared workflow logic
  - `storage/` for persistence and file export
  - `scraper/` for collection and scraping runtime logic
- The main structural problem is not the top-level layout. The problem is that several large files currently mix responsibilities across subdomains:
  - `services/calibration_service.py`
  - `desktop_backend/task_handlers.py`
  - `desktop_backend/server.py`
  - `storage/database.py`
  - `desktop/electron/main.ts`
- There is also a desktop boundary leak where Electron main imports types from a renderer-owned path.

This means the best next step is not "move everything." It is to make the internal boundaries inside each top-level area stricter, then split large files along those boundaries.

## Design Principles

The target structure should follow these rules:

1. One runtime boundary per package area.
   - `desktop/` owns Electron and renderer code only.
   - `desktop_backend/` owns sidecar HTTP and task orchestration only.
   - `services/` owns reusable business workflows.
   - `storage/` owns persistence and export storage details.
   - `scraper/` owns automation/runtime adapters.

2. Shared code should live in shared locations, not in consumer-owned folders.
   - If Electron main and renderer both need a type, it should not live under `renderer/`.

3. Large files should be split by responsibility, not by arbitrary line count.
   - For example, routing, parsing, proxying, and server lifecycle should not stay in one HTTP module just because they are all "backend."

4. Every migration phase must leave the repository runnable.
   - Temporary re-export modules or compatibility imports are acceptable during the refactor.

## Target Repository Shape

```text
desktop/
  electron/
    bootstrap/
    sidecar/
    windows/
    ipc/
    preload.ts
  src/
    shared/
    renderer/
      app/
      features/
        dashboard/
        articles/
        calibration/
        collection/
        scraping/
      components/
      lib/
      state/

desktop_backend/
  app.py
  runtime.py
  http/
    server.py
    routes/
    parsing.py
    responses.py
    image_proxy.py
  tasks/
    registry.py
    events.py
    handlers/
    workers/

services/
  calibration/
  workflows/
  data_transfer/

storage/
  database/
  file_store/

scraper/
  collection/
  scraping/
```

## Target Responsibilities

### `desktop/`

- `electron/` should be responsible for:
  - app bootstrap
  - sidecar process lifecycle
  - BrowserWindow creation
  - IPC and preload wiring
- `src/shared/` should hold types or constants used across Electron and renderer.
- `src/renderer/features/` should group UI code by product feature instead of growing a flat page/component sprawl.

### `desktop_backend/`

- `http/` should contain request parsing, route registration, response helpers, and special-purpose HTTP helpers such as image proxying.
- `tasks/` should contain task orchestration, task events, registry logic, and task-specific workers.
- `app.py` should stay small and primarily compose the server and handlers.

### `services/`

- `calibration/` should become a package because calibration currently mixes:
  - config structure/defaults
  - prompt/request adapters
  - step orchestration
  - desktop automation helpers
- `workflows/` should separate collection and scraping orchestration if those flows continue to grow independently.

### `storage/`

- `database/` should separate schema/migration concerns from query/update concerns while preserving one clear public database API.
- `file_store/` should keep export/render/delete responsibilities, but helpers should be grouped by filename/rendering/storage concerns.

### `scraper/`

- Stage 1 and Stage 2 runtime logic should remain distinct and be grouped by collection vs scraping.
- This package should remain runtime-focused rather than absorbing HTTP or workflow orchestration concerns.

## Staged Migration Plan

### Phase 1: Boundary Extraction

Goal: create clean package boundaries before heavy file movement.

- Move shared desktop types out of renderer-owned paths into a shared desktop location.
- Introduce `desktop_backend/http/` and `desktop_backend/tasks/` packages while preserving current imports through compatibility layers.
- Keep public entry points stable so the app and tests continue to run.

### Phase 2: Big-File Decomposition

Goal: split oversized files using the new package boundaries.

- Split `services/calibration_service.py` into a calibration package.
- Split `desktop_backend/task_handlers.py` into worker- or task-specific modules.
- Split `desktop_backend/server.py` into HTTP server lifecycle, routing, parsing, and image-proxy helpers.
- Split `storage/database.py` into schema/migrations and query/update modules behind one facade.
- Split `desktop/electron/main.ts` into bootstrap, sidecar lifecycle, and window creation modules.

### Phase 3: Feature Alignment

Goal: align file layout with real product domains.

- Group renderer modules under `desktop/src/renderer/features/`.
- Group sidecar task code under domains that mirror desktop workflows:
  - calibration
  - collection
  - scraping
  - articles
- Mirror these domains in tests where that improves discoverability.

### Phase 4: Cleanup

Goal: remove temporary compatibility structure after the new layout is stable.

- Delete re-export shims that only exist for migration.
- Normalize imports to the final package locations.
- Update README, `AGENTS.md`, and relevant developer docs so contributors can follow the new layout.

## Compatibility Rules

To keep the migration safe:

- Each phase must pass relevant tests before the next phase starts.
- Compatibility imports may exist temporarily, but only to preserve a runnable state.
- No phase should combine large file moves with behavior changes unless the behavior change is separately justified and tested.
- Entry points must remain stable:
  - `desktop/electron/main.ts`
  - `desktop/electron/preload.ts`
  - `desktop_backend/app.py`

## Error Handling and Refactor Safety

- Avoid structure-only refactors that accidentally change runtime path resolution, sidecar startup, or task event behavior.
- Keep all existing user-facing APIs stable during structural moves unless there is a separate approved interface change.
- When splitting HTTP and task code, preserve current response contracts and task event shapes.
- When splitting storage modules, avoid changing SQL semantics as part of the same step unless a test-first bugfix requires it.

## Testing and Verification

Minimum verification for each phase:

- Python:
  - `tests.test_desktop_backend_server`
  - `tests.test_desktop_backend_queries`
  - relevant workflow/storage tests for touched modules
- Desktop:
  - `npm --prefix desktop run test`
  - targeted Playwright smoke checks when Electron or preload structure changes
- If a move changes imports only, tests still need to be run to catch subtle runtime or packaging regressions.

## Success Criteria

- Shared code no longer lives under consumer-specific folders when used across runtime boundaries.
- The largest mixed-responsibility files are split into focused packages/modules.
- A new contributor can infer where to place code for:
  - renderer feature work
  - Electron lifecycle work
  - sidecar HTTP work
  - task orchestration
  - workflow logic
  - storage logic
  - scraper runtime logic
- The repository remains runnable and testable after each migration phase.

## Recommended First Refactor Sequence

The first implementation cycle should focus on the highest-leverage boundary work:

1. Shared desktop types extraction
2. `desktop_backend/http/` extraction from `desktop_backend/server.py`
3. `desktop_backend/tasks/` extraction from `desktop_backend/task_handlers.py`
4. `services/calibration/` package split

This order improves structure quickly while minimizing the chance that later domain splits have to undo earlier moves.
