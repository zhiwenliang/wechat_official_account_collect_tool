# Electron Desktop UI Release Notes

This document is the release checklist for the Electron desktop shell and the Python sidecar migration path.

## Developer Startup

- Install the desktop dependencies with `npm --prefix desktop install`.
- Start the Electron shell in dev mode with `npm --prefix desktop run dev`.
- Start the Python backend sidecar in a separate terminal with `python -m desktop_backend.app`.
- Keep using the existing Tkinter UI with `python -m gui.main` when you need a fallback during migration.

## Packaged App Behavior

- The Electron shell first honors `DESKTOP_BACKEND_EXECUTABLE`, then `DESKTOP_BACKEND_PYTHON` for development/testing overrides.
- If no override is set, packaged builds look for a frozen sidecar executable under the Electron resources directory, usually `resources/sidecar/desktop-backend.exe` on Windows.
- If the sidecar cannot be found or fails to spawn, the desktop UI must stay open and show the startup error instead of failing silently.
- The sidecar is expected to resolve writable runtime paths through `utils.runtime_env` so config and data move out of the repository checkout when the backend is frozen.

## Release Checklist

- [ ] `npm --prefix desktop run build` succeeds.
- [ ] `npm --prefix desktop run package:desktop` succeeds.
- [ ] The packaged Electron app starts the Python sidecar.
- [ ] The sidecar resolves runtime config/data paths to the user state directory, not the repo checkout.
- [ ] Startup failures are visible in the Electron UI and in the startup log.
- [ ] `python -m gui.main` still works as the migration fallback.
- [ ] The release notes explain how to point `DESKTOP_BACKEND_EXECUTABLE` at a frozen sidecar when the bundle layout is customized.

## Known Migration Limitations

- The Electron release script currently packages the shell, not a signed Python installer.
- A release pipeline still needs to supply the frozen Python sidecar executable separately or place it at the expected resources path.
- Tkinter remains the supported fallback until the Electron UI fully covers the migration workflows.
