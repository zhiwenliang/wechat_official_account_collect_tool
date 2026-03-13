#!/usr/bin/env python3
"""
Build GUI and/or CLI executables for the current platform with PyInstaller.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCH_ALIASES = {
    "amd64": "x64",
    "x86_64": "x64",
    "arm64": "arm64",
    "aarch64": "arm64",
}

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
COLLECT_SUBMODULE_PACKAGES = (
    "playwright",
    "pyautogui",
    "pyperclip",
    "markdownify",
    "bs4",
    "pyscreeze",
    "pymsgbox",
    "mouseinfo",
    "pytweening",
)
COLLECT_DATA_PACKAGES = (
    "playwright",
    "pyautogui",
    "pyperclip",
    "markdownify",
    "bs4",
    "pyscreeze",
    "pymsgbox",
    "mouseinfo",
    "pytweening",
)
MACOS_HIDDEN_IMPORTS = (
    "Quartz",
    "AppKit",
)
DEFAULT_ICON_PATHS = {
    "Darwin": PROJECT_ROOT / "assets" / "icons" / "wechat-scraper.icns",
    "Windows": PROJECT_ROOT / "assets" / "icons" / "wechat-scraper.ico",
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
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Create a zip archive for each packaged target.",
    )
    return parser.parse_args()


def normalize_arch(arch: str) -> str:
    return ARCH_ALIASES.get(arch.lower(), arch.lower() or "unknown")


def get_platform_tag() -> str:
    system_map = {
        "Darwin": "macos",
        "Windows": "windows",
        "Linux": "linux",
    }
    system_name = system_map.get(platform.system(), platform.system().lower())
    arch = normalize_arch(platform.machine())
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


def get_default_icon_path() -> Path | None:
    """Return the bundled default icon for the current platform when available."""
    icon_path = DEFAULT_ICON_PATHS.get(platform.system())
    if icon_path and icon_path.exists():
        return icon_path
    return None


def resolve_distributable_path(target_key: str, dist_dir: Path) -> Path | None:
    """Return the primary packaged item for the target."""
    target = TARGETS[target_key]
    name = target["name"]

    app_bundle = dist_dir / f"{name}.app"
    if app_bundle.exists():
        return app_bundle

    target_dir = dist_dir / name
    if target_dir.is_dir():
        return target_dir

    for suffix in (".exe", ""):
        executable_path = dist_dir / f"{name}{suffix}"
        if executable_path.is_file():
            return executable_path

    return None


def resolve_runtime_output_dirs(target_key: str, dist_dir: Path) -> list[Path]:
    """Return runtime directories where bundled browsers should be copied."""
    distributable = resolve_distributable_path(target_key, dist_dir)
    if distributable is None:
        return []

    if distributable.suffix == ".app":
        return [distributable / "Contents" / "MacOS"]

    if distributable.is_dir():
        return [distributable]

    return [distributable.parent]


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


def verify_packaged_output(target_key: str, dist_dir: Path) -> Path:
    """Verify the packaged target and bundled Playwright browsers exist."""
    target = TARGETS[target_key]
    distributable = resolve_distributable_path(target_key, dist_dir)
    if distributable is None:
        raise SystemExit(f"未找到 {target_key} 打包产物。预期目录: {dist_dir}")

    if distributable.suffix == ".app":
        executable = distributable / "Contents" / "MacOS" / target["name"]
        if not executable.is_file():
            raise SystemExit(f"未找到 macOS 应用可执行文件: {executable}")
    elif distributable.is_dir():
        candidates = [
            distributable / f"{target['name']}.exe",
            distributable / target["name"],
        ]
        if not any(candidate.is_file() for candidate in candidates):
            raise SystemExit(f"未在目录中找到可执行文件: {distributable}")
    elif not distributable.is_file():
        raise SystemExit(f"未找到可执行文件: {distributable}")

    runtime_dirs = resolve_runtime_output_dirs(target_key, dist_dir)
    if not runtime_dirs:
        raise SystemExit(f"未找到 {target_key} 运行目录，无法校验浏览器资源。")

    for runtime_dir in runtime_dirs:
        browser_dir = runtime_dir / "ms-playwright"
        if not browser_dir.is_dir():
            raise SystemExit(f"缺少 Playwright 浏览器目录: {browser_dir}")

    print(f"Verified packaged output for {target_key}: {distributable}")
    return distributable


def create_zip_archive(source_path: Path, archive_path: Path) -> None:
    """Create a zip archive for the packaged output."""
    if archive_path.exists():
        archive_path.unlink()

    if platform.system() == "Darwin" and source_path.suffix == ".app":
        subprocess.run(
            ["ditto", "-c", "-k", "--keepParent", str(source_path), str(archive_path)],
            check=True,
        )
        return

    shutil.make_archive(
        str(archive_path.with_suffix("")),
        "zip",
        root_dir=source_path.parent,
        base_dir=source_path.name,
    )


def archive_target(target_key: str, dist_dir: Path, platform_tag: str) -> Path:
    """Archive the packaged output into a stable zip artifact."""
    target = TARGETS[target_key]
    distributable = verify_packaged_output(target_key, dist_dir)
    archive_path = dist_dir / f"{target['name']}-{platform_tag}.zip"

    if distributable.is_file():
        with tempfile.TemporaryDirectory(prefix=f"{target['name']}-archive-") as temp_dir:
            temp_root = Path(temp_dir)
            bundle_root = temp_root / target["name"]
            bundle_root.mkdir()
            shutil.copy2(distributable, bundle_root / distributable.name)

            browser_dir = distributable.parent / "ms-playwright"
            if browser_dir.is_dir():
                shutil.copytree(browser_dir, bundle_root / "ms-playwright")

            create_zip_archive(bundle_root, archive_path)
    else:
        create_zip_archive(distributable, archive_path)

    print(f"Created archive: {archive_path}")
    return archive_path


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
    ]

    for package_name in COLLECT_SUBMODULE_PACKAGES:
        pyinstaller_args.extend(["--collect-submodules", package_name])

    for package_name in COLLECT_DATA_PACKAGES:
        pyinstaller_args.extend(["--collect-data", package_name])

    if platform.system() == "Darwin":
        for module_name in MACOS_HIDDEN_IMPORTS:
            pyinstaller_args.extend(["--hidden-import", module_name])

    if target["windowed"]:
        pyinstaller_args.append("--windowed")

    if args.onefile:
        pyinstaller_args.append("--onefile")

    icon_path = args.icon.resolve() if args.icon else get_default_icon_path()
    if icon_path:
        pyinstaller_args.extend(["--icon", str(icon_path)])

    pyinstaller_args.append(str(target["entry"]))

    print(f"\n==> Building {target_key} for {platform_tag}")
    print(f"Using Playwright browsers from: {browser_dir}")
    if icon_path:
        print(f"Using app icon: {icon_path}")
    pyinstaller_run(pyinstaller_args)
    copy_playwright_browsers(target_key, dist_dir, browser_dir)
    verify_packaged_output(target_key, dist_dir)

    if args.archive:
        archive_target(target_key, dist_dir, platform_tag)


def main() -> None:
    args = parse_args()
    platform_tag = get_platform_tag()
    pyinstaller_run = get_pyinstaller_runner()

    targets = ["gui", "cli"] if args.target == "all" else [args.target]
    for target_key in targets:
        build_target(pyinstaller_run, target_key, args, platform_tag)

    print("\nBuild complete.")
    print(f"Output directory: {PROJECT_ROOT / 'dist' / platform_tag}")
    if args.archive:
        print("Distributable archives were created in the output directory.")
    print("Note: package on the target OS; PyInstaller does not cross-compile.")
    print("If content scraping is needed on the target machine, install Chromium with: playwright install chromium")


if __name__ == "__main__":
    main()
