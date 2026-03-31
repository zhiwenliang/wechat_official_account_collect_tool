# Bundled Python Sidecar Packaging Design

**Feature:** package the Electron desktop app as a standalone distributable on macOS and Windows by freezing the Python sidecar and bundling it into the Electron resources directory.

## Scope

- Keep `desktop/` as the only supported user-facing product surface.
- Freeze `desktop_backend` into a native executable on macOS and Windows.
- Bundle the frozen sidecar into Electron packaged builds so end users do not need Python or Conda installed.
- Preserve existing development overrides such as `DESKTOP_BACKEND_EXECUTABLE` and `DESKTOP_BACKEND_PYTHON`.
- Update release documentation so contributors can build complete desktop packages on each supported platform.

## Non-Goals

- Do not add macOS notarization, Developer ID signing, or Windows code signing automation in this change.
- Do not introduce cross-platform build guarantees from a single host machine.
- Do not rewrite backend business logic, scraper behavior, or runtime path handling.
- Do not remove development workflows that launch the sidecar with `python -m desktop_backend.app`.

## Current State

- `desktop/package.json` already packages the Electron shell with `electron-builder`.
- `desktop/electron/backend/launch-spec.ts` already supports packaged mode by looking for a frozen sidecar under `resources/sidecar/` or the resources root.
- `desktop/electron/backend/launch-spec.test.ts` already verifies packaged path resolution behavior.
- Documentation still describes the frozen sidecar as an external prerequisite rather than a built-in packaging step.
- The repository does not yet provide a canonical way to freeze `desktop_backend` into a distributable executable or attach that artifact to Electron packaging.

## Desired Outcome

The supported release flow becomes:

1. Contributor builds the frozen sidecar on the target platform.
2. Contributor packages the Electron app on the same target platform.
3. `electron-builder` includes the sidecar executable under `resources/sidecar/`.
4. The packaged desktop app launches the bundled sidecar automatically with no Python installation on the target machine.

Development flows remain unchanged:

1. `DESKTOP_BACKEND_EXECUTABLE` still overrides all other launch sources.
2. `DESKTOP_BACKEND_PYTHON` still supports local Python debugging.
3. Unpackaged development still falls back to the active Conda environment or `python3`.

## Packaging Architecture

### Sidecar Build Step

Add a dedicated sidecar build pipeline that freezes `desktop_backend.app` into a platform-native executable:

- macOS output name: `desktop-backend`
- Windows output name: `desktop-backend.exe`

The build step should have a stable output directory that Electron packaging can consume without guessing. The output path must be predictable per platform so scripts and docs can reference it directly.

This pipeline should live outside the Electron main-process startup code. Electron should consume a built artifact, not participate in Python freezing.

### Electron Packaging Step

Extend the Electron packaging configuration so packaged builds include the frozen sidecar artifact under the path already supported by runtime discovery:

- `resources/sidecar/desktop-backend`
- `resources/sidecar/desktop-backend.exe`

The packaged app should continue to use the existing launch-resolution order:

1. `DESKTOP_BACKEND_EXECUTABLE`
2. `DESKTOP_BACKEND_PYTHON`
3. active Conda Python in development
4. bundled packaged sidecar

This keeps developer overrides intact while making the packaged app self-contained by default.

### Platform Build Model

The repository should support native packaging on each supported OS:

- build macOS packages on macOS
- build Windows packages on Windows

The change should not promise that macOS can produce Windows installers or vice versa. Documentation should describe native-per-platform builds as the supported path.

## Build Inputs and Runtime Requirements

The frozen sidecar must include everything needed for the desktop backend to start successfully in packaged mode:

- `desktop_backend/`
- shared backend modules used by the sidecar such as `services/`, `storage/`, `scraper/`, and runtime utilities
- any data files or package metadata required by imports at runtime

The packaged sidecar must still respect the existing runtime environment behavior:

- use `utils.runtime_env` for config and data directories
- write runtime data outside the repository checkout
- accept `--host` and `--port` arguments exactly as the current Python module entrypoint does

## Validation Strategy

Add focused validation for the new packaging contract:

- tests that verify the Electron packaging configuration includes the sidecar resource path
- tests or script checks that verify the sidecar build output uses the expected executable name and location
- existing launch-spec tests continue to protect runtime resolution behavior

Manual verification for each platform should confirm:

- sidecar build command succeeds
- Electron packaging command succeeds
- packaged app launches and reaches backend ready state
- runtime data is written to the user state directory rather than the repo

## Documentation Changes

Update `README.md` and `docs/electron-desktop-ui.md` to describe the new canonical packaging flow:

- native platform build requirement
- sidecar build command
- packaged desktop build command
- where the frozen sidecar is expected inside packaged resources
- what remains configurable with `DESKTOP_BACKEND_EXECUTABLE`

Contributor-facing docs may still mention direct Python startup, but only as a development and debugging workflow.

## Risks and Mitigations

### Missing Frozen Dependencies

Risk: the sidecar executable builds successfully but fails at runtime because PyInstaller misses hidden imports or data files.

Mitigation:

- keep the sidecar build configuration explicit
- validate startup through packaged-app smoke checks
- document any platform-specific packaging prerequisites clearly

### Packaging Drift

Risk: sidecar output paths drift from the Electron resource paths expected by runtime discovery.

Mitigation:

- define one canonical output location for the sidecar build
- wire Electron packaging to that exact location
- add regression coverage for path conventions

### Overloading Startup Logic

Risk: implementation spreads packaging concerns into runtime launch code and makes development paths harder to understand.

Mitigation:

- keep freezing and packaging in dedicated scripts/configuration
- keep `launch-spec.ts` focused on selection of an already-built backend

## Success Criteria

- Contributors can build a complete macOS desktop package on macOS without requiring Python on the destination machine.
- Contributors can build a complete Windows desktop package on Windows without requiring Python on the destination machine.
- Packaged Electron builds contain the frozen sidecar under `resources/sidecar/`.
- The packaged desktop app starts the bundled sidecar successfully using the existing runtime discovery logic.
- README and release documentation describe the bundled-sidecar packaging flow as the canonical distribution path.
