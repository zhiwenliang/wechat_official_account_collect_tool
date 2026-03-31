# Electron Desktop Release Notes

This document describes the supported Electron desktop product and the Python sidecar it depends on.

## Developer Startup

- Install frontend dependencies with `npm --prefix desktop install`.
- For **development and debugging only**, start the Python sidecar with `python -m desktop_backend.app` when you want backend logs in a separate terminal (not the end-user workflow).
- Start the Electron development app with `npm --prefix desktop run dev`.

## Sidecar Resolution Rules

The Electron main process resolves the backend in this order:

1. `DESKTOP_BACKEND_EXECUTABLE`
2. `DESKTOP_BACKEND_PYTHON`
3. Python inside the active Conda environment
4. A packaged sidecar executable under the Electron resources directory

If the backend cannot be found or fails to start, the Electron app must stay open and show the startup error.

## Building the frozen sidecar only

- `npm --prefix desktop run build:sidecar` runs `desktop/scripts/build-sidecar.mjs`, which invokes `python scripts/build_desktop_sidecar.py` from the **repository root** (same as the pre-step inside `package:desktop`).
- Use this when you want `build/desktop-sidecar/` refreshed without running electron-builder.

## Packaged App Behavior

- A **standalone distributable requires the frozen Python sidecar** bundled inside the Electron app. Running `npm --prefix desktop run package:desktop` (or `package:desktop:dir`) builds that sidecar first (same as `npm --prefix desktop run build:sidecar`, i.e. `python scripts/build_desktop_sidecar.py` from the repo root), then packages the shell; PyInstaller emits an **onedir** bundle under **`build/desktop-sidecar/desktop-backend/`**, and electron-builder copies **`resources/sidecar/desktop-backend/**`** plus browsers. The runnable entry is **`resources/sidecar/desktop-backend/desktop-backend`** (macOS/Linux) or **`resources/sidecar/desktop-backend/desktop-backend.exe`** (Windows).
- **Playwright Chromium for packaged scraping:** the build machine must run **`playwright install chromium`** before `build:sidecar` / `package:desktop`. The sidecar build copies **Chromium-related** entries from the local Playwright cache (`chromium-*`, `chromium_headless_shell-*`, `ffmpeg-*` when present) into `build/desktop-sidecar/ms-playwright/`, omitting other browsers such as Firefox or WebKit. extraResources ships **`resources/sidecar/ms-playwright/`** next to the onedir folder. On startup, `configure_runtime_environment()` sets **`PLAYWRIGHT_BROWSERS_PATH`** for frozen runs when that directory is present (unless already set).
- **Native platform builds:** produce the macOS artifact on macOS and the Windows artifact on Windows. Do not rely on cross-compiling the frozen Python sidecar or native Node modules; validate on each **native platform** before release.
- Packaged builds resolve the sidecar under the Electron resources directory; preferred layout is **`resources/sidecar/desktop-backend/<binary>`**. Legacy single-file layouts under `resources/sidecar/desktop-backend` (file) are still accepted when present.
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

- The Electron build packages the shell and frontend resources, not a signed Python installer from python.org.
- Packaged scraping assumes the **same OS family** as the build machine that ran `playwright install chromium` (staged under `ms-playwright`). Switching OS or Playwright major versions may require a fresh install and rebuild.
- CI must run `package:desktop` on the **native platform** it targets, with the `wechat-scraper` Conda env (or `DESKTOP_BACKEND_PYTHON`), and must run **`playwright install chromium`** before the sidecar build so `ms-playwright` can be staged.
