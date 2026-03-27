# Electron Desktop Release Notes

This document describes the supported Electron desktop product and the Python sidecar it depends on.

## Developer Startup

- Install frontend dependencies with `npm --prefix desktop install`.
- Start the Python sidecar with `python -m desktop_backend.app` when you want backend logs in a separate terminal.
- Start the Electron development app with `npm --prefix desktop run dev`.

## Sidecar Resolution Rules

The Electron main process resolves the backend in this order:

1. `DESKTOP_BACKEND_EXECUTABLE`
2. `DESKTOP_BACKEND_PYTHON`
3. Python inside the active Conda environment
4. A packaged sidecar executable under the Electron resources directory

If the backend cannot be found or fails to start, the Electron app must stay open and show the startup error.

## Packaged App Behavior

- Packaged builds look for a frozen sidecar under the Electron resources directory, typically `resources/sidecar/desktop-backend.exe` on Windows.
- The sidecar resolves runtime config and data paths through `utils.runtime_env`, so packaged builds write outside the repository checkout.
- Startup failures should be visible both in the UI and in the startup log.

## Release Checklist

- [ ] `npm --prefix desktop run build` succeeds.
- [ ] `npm --prefix desktop run package:desktop` succeeds.
- [ ] The packaged Electron app starts the Python sidecar successfully.
- [ ] Runtime config and data are written to the user state directory.
- [ ] Startup failures are visible in the Electron UI and log output.
- [ ] The release notes explain how to override sidecar discovery with `DESKTOP_BACKEND_EXECUTABLE`.

## Known Limitations

- The Electron build packages the shell and frontend resources, not a signed Python installer.
- Release automation still needs to provide the frozen Python sidecar executable or place it at the expected resources path.
