from __future__ import annotations

import sys
from pathlib import Path

PACKAGED_EXECUTABLE_STEM = "desktop-backend"
BUILD_OUTPUT_SEGMENTS = ("build", "desktop-sidecar")
PLAYWRIGHT_STAGING_DIRNAME = "ms-playwright"

# Top-level repo packages the sidecar imports at runtime (explicit PyInstaller graph).
SIDECAR_SOURCE_PACKAGES = (
    "desktop_backend",
    "services",
    "storage",
    "scraper",
    "utils",
)


def packaged_executable_basename(platform: str | None = None) -> str:
    plat = platform if platform is not None else sys.platform
    if plat == "win32":
        return f"{PACKAGED_EXECUTABLE_STEM}.exe"
    return PACKAGED_EXECUTABLE_STEM


def packaged_executable_path(repo_root: Path, platform: str | None = None) -> Path:
    """Path to the PyInstaller onedir console binary (folder + executable name)."""
    return (
        build_output_dir(repo_root)
        / PACKAGED_EXECUTABLE_STEM
        / packaged_executable_basename(platform)
    )


def build_output_dir(repo_root: Path) -> Path:
    return repo_root.joinpath(*BUILD_OUTPUT_SEGMENTS)


def playwright_staging_dir(repo_root: Path) -> Path:
    return build_output_dir(repo_root) / PLAYWRIGHT_STAGING_DIRNAME


def pyinstaller_work_dir(repo_root: Path) -> Path:
    return repo_root / "build" / ".pyi-desktop-sidecar"
