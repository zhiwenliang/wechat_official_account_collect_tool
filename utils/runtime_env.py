"""
Runtime environment helpers for packaged executables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_runtime_roots() -> list[Path]:
    roots = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    executable = getattr(sys, "executable", None)
    if executable:
        roots.append(Path(executable).resolve().parent)

    roots.append(Path(__file__).resolve().parents[1])
    return roots


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
