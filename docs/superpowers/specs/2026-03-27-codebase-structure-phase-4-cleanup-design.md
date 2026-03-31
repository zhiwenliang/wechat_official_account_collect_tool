# Phase 4 Cleanup Design

**Feature:** finish the codebase structure migration by removing temporary compatibility shims, normalizing imports to the final domain layout, and aligning contributor docs with the actual post-Phase-3 tree.

## Scope

- Remove migration-only compatibility modules that still exist solely to preserve old import paths.
- Normalize internal imports to the final Phase 3 domain paths.
- Update structural tests so they verify final ownership boundaries instead of temporary re-export identities.
- Update `README.md`, `AGENTS.md`, `CLAUDE.md`, and other relevant contributor-facing docs so they describe the same final layout.
- Keep the supported runtime entry points stable while the cleanup is performed.

## Non-Goals

- Do not redesign desktop workflows, HTTP contracts, task event payloads, or runtime behavior.
- Do not move feature code into new domains beyond what Phase 3 already established.
- Do not rewrite shared workflow logic out of `services/`, persistence logic out of `storage/`, or runtime adapters out of `scraper/`.
- Do not introduce new public compatibility layers; this phase is about removing them.

## Current State

Phase 3 established the target domain layout, but the repo still carries migration-only compatibility surfaces:

- Renderer feature code already lives under `desktop/src/renderer/features/`.
- Article backend code already lives under `desktop_backend/articles/`.
- Calibration backend code already lives under `desktop_backend/tasks/calibration/`.
- Collection and scraping runner code already lives under `desktop_backend/tasks/collection/` and `desktop_backend/tasks/scraping/`.

The remaining structural debt is that several old paths still exist only as shims:

- `desktop_backend/task_handlers.py`
- `desktop_backend/tasks/__init__.py`
- `desktop_backend/tasks/events.py`
- `desktop_backend/tasks/handlers.py`
- `desktop_backend/tasks/registry.py`
- `desktop_backend/tasks/calibration_worker.py`
- `desktop_backend/query_handlers.py` and `desktop_backend/schemas.py` still serve as mixed shared modules plus compatibility re-export surfaces

This keeps the repo runnable, but it also makes the real ownership harder to follow because the old and new layouts both appear valid.

## Design Principles

1. One canonical import path per responsibility.
   - If code lives under `desktop_backend/articles/`, internal imports should point there directly.
   - If code lives under `desktop_backend/tasks/calibration/`, internal imports should point there directly.

2. Remove only migration-only structure.
   - Delete shims that exist purely to preserve an old path.
   - Keep shared infrastructure modules that still own real behavior.

3. Preserve runtime entry points.
   - `desktop/electron/main.ts`, `desktop/electron/preload.ts`, and `desktop_backend/app.py` remain stable.
   - Cleanup must not change user-facing startup or API behavior.

4. Let tests prove the final shape.
   - Structural tests should verify the final ownership boundaries directly.
   - Tests whose only purpose was to prove temporary compatibility re-exports should be rewritten or removed.

5. Finish the migration story in docs.
   - Contributor docs should describe one final structure, not a mixture of pre- and post-migration guidance.

## Target Phase 4 State

After Phase 4:

- Renderer imports use `desktop/src/renderer/features/*` directly and no legacy `pages/` references remain.
- Article code is referenced through `desktop_backend/articles/*`.
- Calibration code is referenced through `desktop_backend/tasks/calibration/*`.
- Collection and scraping runner code is referenced through `desktop_backend/tasks/{collection,scraping}/*`.
- Temporary top-level and package-level compatibility modules used only during migration are removed.
- Structural tests assert the final module locations rather than re-export identity.
- `README.md`, `AGENTS.md`, and `CLAUDE.md` all describe the same final repo layout.

## Cleanup Targets

### Remove

These modules should be deleted if they are only compatibility shims by the time implementation begins:

- `desktop_backend/task_handlers.py`
- `desktop_backend/tasks/__init__.py`
- `desktop_backend/tasks/events.py`
- `desktop_backend/tasks/handlers.py`
- `desktop_backend/tasks/registry.py`
- `desktop_backend/tasks/calibration_worker.py`

Additional cleanup may include trimming `desktop_backend/query_handlers.py`, `desktop_backend/schemas.py`, or `desktop_backend/__init__.py` if any remaining exports exist only for migration and no longer own shared logic.

### Keep

These modules stay because they still represent real entry points or shared infrastructure:

- `desktop_backend/app.py`
- `desktop_backend/runtime.py`
- `desktop_backend/server.py`
- `desktop_backend/server_runtime.py`
- `desktop_backend/server_routes.py`
- `desktop_backend/server_json.py`
- `desktop_backend/http/*`
- `desktop_backend/import_export_handlers.py`
- `desktop_backend/task_registry.py`
- `desktop_backend/task_events.py`
- `desktop_backend/tasks/defaults.py` if it still owns real shared factories after shim removal

This keep list is intentionally non-exhaustive. The Phase 4 rule is to delete only paths that have been explicitly validated as shim-only.

## Final Ownership Rules

### Renderer

- Feature pages and feature-owned tests remain under `desktop/src/renderer/features/*`.
- Cross-feature UI remains under `desktop/src/renderer/components/`.
- Shared renderer transport and utility code remains under `desktop/src/renderer/lib/`.
- Shared renderer state remains under `desktop/src/renderer/state/`.
- Cross-runtime desktop contracts remain under `desktop/src/shared/`.

### Sidecar

- Article-facing query and command handlers live under `desktop_backend/articles/`.
- Calibration worker, runtime, and calibration-status logic live under `desktop_backend/tasks/calibration/`.
- Collection runner logic lives under `desktop_backend/tasks/collection/`.
- Scraping runner logic lives under `desktop_backend/tasks/scraping/`.
- Shared task coordination remains under the shared task infrastructure modules that still own real behavior.
- `desktop_backend/task_registry.py` and `desktop_backend/task_events.py` are the canonical shared task infrastructure paths after Phase 4.
- The older repo-wide ASCII tree that showed `desktop_backend/tasks/registry.py` and `desktop_backend/tasks/events.py` should be treated as stale diagram detail, not as the intended final import surface.

## Test Strategy

Phase 4 should update tests to reflect the final layout:

- Structural tests should assert the final canonical module locations and contracts.
- Re-export identity tests that only existed to protect temporary shims should be removed once those shims are deleted.
- Behavior tests for article queries, calibration tasks, collection tasks, and scraping tasks should continue to run unchanged unless a test imports a deleted shim path.
- Renderer tests should continue to import feature modules from `features/*` only.

## Documentation Strategy

The final docs should tell one consistent story:

- `README.md` should describe the supported product and the final high-level layout contributors will see.
- `AGENTS.md` should describe the final landing zones for renderer and sidecar code.
- `CLAUDE.md` should align with the same post-Phase-4 tree and avoid pointing agents at removed shim modules.
- Any remaining structure notes in Phase 3-specific docs can remain historical records, but active contributor guidance should reference only the final layout.

## Compatibility and Safety

- Do not remove a shim until all in-repo imports and tests that depend on it have been updated.
- Keep `desktop_backend/app.py` behavior stable while changing import targets underneath it.
- Keep HTTP routes, JSON payloads, and task event semantics unchanged.
- Keep `desktop/electron/main.ts` and `desktop/electron/preload.ts` stable; Phase 4 is not an Electron bootstrap redesign.
- Do not treat `desktop_backend/query_handlers.py` or `desktop_backend/schemas.py` as pure shim barrels unless their remaining shared statistics ownership has first been relocated to an intentional final home.
- If `StatisticsPayload`, `build_statistics_payload`, or `get_statistics_handler` move during cleanup, that relocation must be explicit, behavior-preserving, and covered by tests in the same change.
- If `desktop_backend/tasks/__init__.py` remains after shim removal, it must expose only the final intended public surface rather than forwarding legacy aliases implicitly.

## Verification

Minimum verification for Phase 4:

- Python:
  - `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure -v`
  - `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_server -v`
  - `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries -v`
  - `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_tasks -v`
  - `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
- Desktop:
  - `npm --prefix desktop run typecheck`
  - `npm --prefix desktop run test`
- Import cleanup:
  - search the repo for removed shim paths and confirm no remaining in-repo references

## Success Criteria

- Migration-only compatibility shims are removed.
- In-repo imports point to the final canonical module paths.
- Structural tests reflect the final ownership boundaries rather than temporary re-export identity.
- Contributor docs describe one final repo layout consistently.
- All required verification passes after cleanup.
