# Electron-Only Product Cutover Design

**Feature:** turn the repository into a strict Electron desktop product where users launch only the desktop app and never run Python commands directly.

## Scope

- Keep Electron + React in `desktop/` as the only supported user-facing application.
- Keep Python automation and data logic as an internal sidecar behind `desktop_backend/`.
- Remove legacy user-facing entry points that imply multiple supported products.
- Rewrite documentation and packaging guidance around the Electron desktop app only.

## Non-Goals

- Do not rewrite scraper, calibration, storage, or workflow logic out of Python.
- Do not redesign the desktop UI information architecture unless required by the cutover.
- Do not preserve Tkinter or CLI as supported fallback workflows.

## Current State

- The repo already contains a working Electron workspace in `desktop/`.
- The Python desktop sidecar already exists in `desktop_backend/`.
- Legacy surfaces still remain in the repository and documentation:
  - `gui/` Tkinter application
  - `main.py` CLI entry point
  - Tkinter and CLI tests
  - README and release notes that still describe Tkinter fallback and manual Python command workflows

This leaves the product boundary ambiguous. The codebase needs a single supported surface.

## Target Product Boundary

The product has one supported launch path:

1. User installs or launches the Electron desktop app.
2. Electron starts the bundled or configured Python sidecar.
3. The sidecar owns calibration, collection, scraping, import/export, and database access.
4. The renderer exposes all required workflows through the desktop UI.

Users do not interact with Python directly. Python remains an implementation detail.

## Repository Boundary Changes

### Keep

- `desktop/`
- `desktop_backend/`
- `scraper/`
- `services/`
- `storage/`
- shared utilities required by the sidecar
- backend and desktop tests that validate the Electron-supported product

### Remove

- `gui/`
- `main.py`
- CLI-specific tests and Tkinter-specific tests
- Tkinter-only helper modules that are no longer referenced
- documentation that describes Tkinter fallback or user-run Python commands as supported usage

### Reframe as Internal

- `scraper/`, `services/`, `storage/`, and backend runtime helpers stay in the repository, but only as internals of the sidecar-backed desktop app.

## Documentation Changes

The README and desktop release notes should describe a single story:

- install desktop dependencies
- run the Electron desktop app in development
- package the Electron app for distribution
- explain how the sidecar is located and started by Electron

Contributor-facing notes may still mention direct backend startup for diagnostics or local development, but they must be clearly framed as internal development details rather than end-user workflows.

## Packaging Changes

- The Electron packaging path becomes the canonical distribution path.
- Packaging docs should assume the product is delivered as a desktop app with an attached sidecar arrangement.
- Tkinter and CLI packaging guidance should be removed.
- Any remaining release notes should describe how Electron locates the sidecar in development and packaged modes.

## Compatibility and Risk

The main risk is deleting a legacy entry point that is still referenced somewhere in the desktop-backed flow. To control that risk:

- remove only code that is no longer referenced by Electron or `desktop_backend`
- verify backend tests that cover sidecar handlers and workflow/storage behavior
- verify desktop checks that cover build or test flows for the supported app

This keeps the implementation focused on product-surface cleanup rather than backend rewrites.

## Implementation Outline

### Phase 1: Cut unsupported entry points

- delete `gui/`
- delete `main.py`
- delete Tkinter-only and CLI-only tests/helpers

### Phase 2: Rewrite docs and release guidance

- update `README.md` to present Electron as the only supported product
- update Electron release notes to remove migration language and fallback references
- remove packaging instructions that build GUI or CLI as separate products

### Phase 3: Verify supported flows

- run relevant Python tests for `desktop_backend`, storage, and workflows
- run Electron checks for the desktop workspace
- confirm no remaining supported docs instruct users to run Python commands directly

## Testing and Verification

Minimum verification for this cutover:

- backend unit tests covering `desktop_backend`
- workflow and storage tests still used by the sidecar
- desktop `typecheck`, `test`, or other fast checks that define the Electron product baseline

If any legacy tests fail only because they target removed CLI or Tkinter entry points, those tests should be deleted rather than repaired.

## Success Criteria

- The repository documents one supported product: the Electron desktop app.
- No user-facing docs instruct end users to run `python main.py ...` or `python -m gui.main`.
- Legacy Tkinter and CLI entry points are removed from the repository.
- Remaining code and tests align with Electron + sidecar as the supported architecture.
