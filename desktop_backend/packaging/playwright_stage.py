"""Stage Playwright browser bundles next to the PyInstaller sidecar output."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


class PlaywrightBrowsersNotFoundError(FileNotFoundError):
    """No installed Playwright browsers found to stage."""


def is_staged_ms_playwright_top_level(name: str) -> bool:
    """Whether a cache entry should be copied for Chromium-sidecar packaging."""
    if name.startswith("chromium-"):
        return True
    if name.startswith("chromium_headless_shell-"):
        return True
    if name.startswith("ffmpeg-"):
        return True
    return False


def ms_playwright_root_has_chromium_revision_dir(root: Path) -> bool:
    """True if root looks like a Playwright cache with at least one Chromium build."""
    if not root.is_dir():
        return False
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith("chromium-"):
            return True
    return False


def ms_playwright_root_from_chromium_executable(executable: Path) -> Path | None:
    """Walk parents from the Chromium binary until a directory named ms-playwright."""
    resolved = executable.resolve()
    for ancestor in (resolved, *resolved.parents):
        if ancestor.name == "ms-playwright" and ancestor.is_dir():
            return ancestor
    return None


def resolve_via_playwright_chromium_executable() -> Path | None:
    """Resolve the browser root using Playwright's installed Chromium executable path."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as playwright:
            raw = playwright.chromium.executable_path
    except Exception:
        return None
    if not raw:
        return None
    exe_path = Path(raw).expanduser()
    try:
        exe_resolved = exe_path.resolve()
    except OSError:
        return None
    if not exe_resolved.is_file():
        return None
    root = ms_playwright_root_from_chromium_executable(exe_resolved)
    if root is None or not root.is_dir():
        return None
    if not ms_playwright_root_has_chromium_revision_dir(root):
        return None
    return root


def _accept_ms_playwright_root(path: Path) -> Path | None:
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        return None
    if not ms_playwright_root_has_chromium_revision_dir(resolved):
        return None
    return resolved


def resolve_installed_playwright_browsers_dir() -> Path | None:
    explicit = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if explicit:
        accepted = _accept_ms_playwright_root(Path(explicit))
        if accepted is not None:
            return accepted

    via_playwright = resolve_via_playwright_chromium_executable()
    if via_playwright is not None:
        return via_playwright

    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        if local:
            candidate = Path(local) / "ms-playwright"
            accepted = _accept_ms_playwright_root(candidate)
            if accepted is not None:
                return accepted
    elif sys.platform == "darwin":
        candidate = Path.home() / "Library" / "Caches" / "ms-playwright"
        accepted = _accept_ms_playwright_root(candidate)
        if accepted is not None:
            return accepted
    else:
        candidate = Path.home() / ".cache" / "ms-playwright"
        accepted = _accept_ms_playwright_root(candidate)
        if accepted is not None:
            return accepted

    return None


def stage_playwright_browsers(build_output_dir: Path) -> Path:
    """Copy Chromium-related Playwright cache entries into build_output_dir/ms-playwright."""
    src = resolve_installed_playwright_browsers_dir()
    if src is None:
        raise PlaywrightBrowsersNotFoundError(
            "No Playwright browser cache found. Run: playwright install chromium "
            "(or set PLAYWRIGHT_BROWSERS_PATH to an existing ms-playwright "
            "directory).",
        )

    dest = build_output_dir / "ms-playwright"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    staged_chromium = False
    for child in sorted(src.iterdir(), key=lambda p: p.name):
        if not is_staged_ms_playwright_top_level(child.name):
            continue
        target = dest / child.name
        if child.is_dir():
            shutil.copytree(child, target, symlinks=True)
        else:
            shutil.copy2(child, target)
        if child.name.startswith("chromium-"):
            staged_chromium = True

    if not staged_chromium:
        shutil.rmtree(dest)
        raise PlaywrightBrowsersNotFoundError(
            "Playwright cache had no chromium-* payload to stage after filtering. "
            "Run: playwright install chromium",
        )

    return dest
