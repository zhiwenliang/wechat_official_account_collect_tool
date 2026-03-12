#!/usr/bin/env python3
"""
Build GUI and/or CLI executables for the current platform with PyInstaller.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TARGETS = {
    "gui": {
        "name": "wechat-scraper-gui",
        "entry": PROJECT_ROOT / "gui" / "main.py",
        "windowed": True,
    },
    "cli": {
        "name": "wechat-scraper-cli",
        "entry": PROJECT_ROOT / "main.py",
        "windowed": False,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package the project as executables.")
    parser.add_argument(
        "--target",
        choices=["gui", "cli", "all"],
        default="all",
        help="Which executable target to build.",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build one-file executables instead of onedir bundles.",
    )
    parser.add_argument(
        "--icon",
        type=Path,
        help="Optional icon path passed through to PyInstaller.",
    )
    return parser.parse_args()


def get_platform_tag() -> str:
    system_map = {
        "Darwin": "macos",
        "Windows": "windows",
        "Linux": "linux",
    }
    system_name = system_map.get(platform.system(), platform.system().lower())
    arch = platform.machine().lower() or "unknown"
    return f"{system_name}-{arch}"


def find_playwright_browser_dir() -> Path:
    candidates = []

    env_value = None
    try:
        import os
        env_value = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    except Exception:
        env_value = None

    if env_value:
        candidates.append(Path(env_value).expanduser())

    home = Path.home()
    candidates.extend([
        home / "Library" / "Caches" / "ms-playwright",
        home / ".cache" / "ms-playwright",
        home / "AppData" / "Local" / "ms-playwright",
    ])

    for candidate in candidates:
        if not candidate.exists():
            continue

        chromium_dirs = [child for child in candidate.iterdir() if child.is_dir() and child.name.startswith("chromium-")]
        if chromium_dirs:
            return candidate

    print(
        "未找到 Playwright Chromium 浏览器目录。请先在当前打包环境执行: playwright install chromium",
        file=sys.stderr,
    )
    raise SystemExit(1)


def get_pyinstaller_runner():
    try:
        from PyInstaller.__main__ import run as pyinstaller_run
    except ImportError as exc:
        print("PyInstaller 未安装。请先执行: pip install pyinstaller", file=sys.stderr)
        raise SystemExit(1) from exc
    return pyinstaller_run


def resolve_runtime_output_dirs(target_key: str, dist_dir: Path) -> list[Path]:
    """Return runtime directories where bundled browsers should be copied."""
    target = TARGETS[target_key]
    name = target["name"]
    destinations = []

    mac_app_dir = dist_dir / f"{name}.app" / "Contents" / "MacOS"
    if mac_app_dir.exists():
        destinations.append(mac_app_dir)

    target_dir = dist_dir / name
    if target_dir.is_dir():
        destinations.append(target_dir)

    executable_suffixes = ["", ".exe"]
    for suffix in executable_suffixes:
        executable_path = dist_dir / f"{name}{suffix}"
        if executable_path.is_file():
            destinations.append(executable_path.parent)

    unique_destinations = []
    seen = set()
    for destination in destinations:
        resolved = destination.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_destinations.append(destination)

    return unique_destinations


def copy_playwright_browsers(target_key: str, dist_dir: Path, browser_dir: Path) -> None:
    """Copy Playwright browsers next to the packaged runtime."""
    destinations = resolve_runtime_output_dirs(target_key, dist_dir)
    if not destinations:
        print(
            f"未找到 {target_key} 打包产物的运行目录，跳过复制浏览器目录。",
            file=sys.stderr,
        )
        return

    for runtime_dir in destinations:
        target_dir = runtime_dir / "ms-playwright"
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(browser_dir, target_dir)
        print(f"Copied Playwright browsers to: {target_dir}")


def build_target(pyinstaller_run, target_key: str, args: argparse.Namespace, platform_tag: str) -> None:
    target = TARGETS[target_key]
    dist_dir = PROJECT_ROOT / "dist" / platform_tag
    work_dir = PROJECT_ROOT / "build" / platform_tag / target_key
    spec_dir = PROJECT_ROOT / "build" / "specs"
    browser_dir = find_playwright_browser_dir()

    pyinstaller_args = [
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        "--paths",
        str(PROJECT_ROOT),
        "--name",
        target["name"],
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "PIL._tkinter_finder",
        "--collect-submodules",
        "playwright",
        "--collect-data",
        "playwright",
    ]

    if target["windowed"]:
        pyinstaller_args.append("--windowed")

    if args.onefile:
        pyinstaller_args.append("--onefile")

    if args.icon:
        pyinstaller_args.extend(["--icon", str(args.icon.resolve())])

    pyinstaller_args.append(str(target["entry"]))

    print(f"\n==> Building {target_key} for {platform_tag}")
    print(f"Using Playwright browsers from: {browser_dir}")
    pyinstaller_run(pyinstaller_args)
    copy_playwright_browsers(target_key, dist_dir, browser_dir)


def main() -> None:
    args = parse_args()
    platform_tag = get_platform_tag()
    pyinstaller_run = get_pyinstaller_runner()

    targets = ["gui", "cli"] if args.target == "all" else [args.target]
    for target_key in targets:
        build_target(pyinstaller_run, target_key, args, platform_tag)

    print("\nBuild complete.")
    print(f"Output directory: {PROJECT_ROOT / 'dist' / platform_tag}")
    print("Note: package on the target OS; PyInstaller does not cross-compile.")
    print("If content scraping is needed on the target machine, install Chromium with: playwright install chromium")


if __name__ == "__main__":
    main()
