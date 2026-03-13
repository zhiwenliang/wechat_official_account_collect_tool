"""
Runtime environment helpers for packaged executables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


APP_STATE_DIRNAME = "WeChatScraper"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _candidate_runtime_roots() -> list[Path]:
    roots = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    executable = getattr(sys, "executable", None)
    if executable:
        roots.append(Path(executable).resolve().parent)

    roots.append(REPO_ROOT)
    return roots


def get_runtime_state_root() -> Path:
    """Return the writable root used for config/data files."""
    if not getattr(sys, "frozen", False):
        return REPO_ROOT

    if sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    state_root = base_dir / APP_STATE_DIRNAME
    state_root.mkdir(parents=True, exist_ok=True)
    return state_root


def resolve_runtime_path(relative_path: str | Path) -> Path:
    """Resolve a repo-relative runtime path to a writable location when frozen."""
    path = Path(relative_path)
    if path.is_absolute():
        return path

    return get_runtime_state_root() / path


def configure_runtime_environment() -> None:
    """Configure runtime paths when running from a packaged bundle."""
    if not getattr(sys, "frozen", False):
        return

    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    for root in _candidate_runtime_roots():
        browser_dir = root / "ms-playwright"
        if browser_dir.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_dir)
            return
