"""Console entry for PyInstaller desktop-backend bundles (onedir or legacy onefile)."""

from __future__ import annotations

from desktop_backend.app import main

if __name__ == "__main__":
    raise SystemExit(main())
