#!/usr/bin/env python3
"""Build the desktop backend sidecar with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    sys.path.insert(0, str(REPO_ROOT))
    from desktop_backend.packaging import build_config
    from desktop_backend.packaging.playwright_stage import (
        PlaywrightBrowsersNotFoundError,
        stage_playwright_browsers,
    )

    spec = REPO_ROOT / "desktop_backend" / "packaging" / "desktop-backend.spec"
    dist = build_config.build_output_dir(REPO_ROOT)
    work = build_config.pyinstaller_work_dir(REPO_ROOT)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec),
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist),
        "--workpath",
        str(work),
    ]
    cmd.extend(argv)
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    try:
        stage_playwright_browsers(dist)
    except PlaywrightBrowsersNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
