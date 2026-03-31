# Bundled Python Sidecar Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete Electron desktop distributable that includes a frozen Python sidecar on macOS and Windows so end users do not need Python installed.

**Architecture:** Add a dedicated PyInstaller-based sidecar build pipeline under repository-level packaging helpers, emit one canonical artifact under `build/desktop-sidecar/`, and have Electron packaging copy that artifact into `resources/sidecar/` using the runtime contract already supported by `launch-spec.ts`.

**Tech Stack:** Python 3.10, PyInstaller, Electron Builder, Node.js, TypeScript, unittest, Vitest

---

### Task 1: Define the sidecar build contract

**Files:**
- Create: `desktop_backend/packaging/build_config.py`
- Create: `desktop_backend/packaging/entrypoint.py`
- Create: `desktop_backend/packaging/desktop-backend.spec`
- Create: `scripts/build_desktop_sidecar.py`
- Modify: `requirements.txt`
- Test: `tests/test_desktop_sidecar_packaging.py`

- [ ] **Step 1: Write the failing packaging contract test**

```python
from pathlib import Path
import unittest

from desktop_backend.packaging.build_config import (
    build_output_dir,
    packaged_executable_name,
)


class DesktopSidecarPackagingTests(unittest.TestCase):
    def test_packaged_executable_name_matches_platform(self) -> None:
        self.assertEqual(packaged_executable_name("darwin"), "desktop-backend")
        self.assertEqual(packaged_executable_name("win32"), "desktop-backend.exe")

    def test_build_output_dir_is_stable(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        self.assertEqual(build_output_dir(repo_root), repo_root / "build" / "desktop-sidecar")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_sidecar_packaging -v`

Expected: FAIL with `ModuleNotFoundError` for `desktop_backend.packaging.build_config`

- [ ] **Step 3: Implement the packaging contract helpers and frozen entrypoint**

```python
# desktop_backend/packaging/build_config.py
from __future__ import annotations

from pathlib import Path


def packaged_executable_name(platform: str) -> str:
    return "desktop-backend.exe" if platform == "win32" else "desktop-backend"


def build_output_dir(repo_root: Path) -> Path:
    return repo_root / "build" / "desktop-sidecar"


def pyinstaller_work_dir(repo_root: Path) -> Path:
    return repo_root / "build" / "pyinstaller"
```

```python
# desktop_backend/packaging/entrypoint.py
from desktop_backend.app import main


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add the PyInstaller spec and the build runner**

```python
# desktop_backend/packaging/desktop-backend.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.building.build_main import Analysis, EXE, PYZ
from PyInstaller.config import CONF

project_root = Path(__file__).resolve().parents[2]
entrypoint = project_root / "desktop_backend" / "packaging" / "entrypoint.py"
dist_dir = project_root / "build" / "desktop-sidecar"
work_dir = project_root / "build" / "pyinstaller"

hiddenimports = collect_submodules("desktop_backend")
hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("storage")
hiddenimports += collect_submodules("scraper")
hiddenimports += collect_submodules("utils")

datas = []
for package_name in ("desktop_backend", "services", "storage", "scraper", "utils"):
    datas += collect_data_files(package_name)

CONF["distpath"] = str(dist_dir)
CONF["workpath"] = str(work_dir)

a = Analysis(
    [str(entrypoint)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="desktop-backend",
    console=True,
)
```

```python
# scripts/build_desktop_sidecar.py
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

from desktop_backend.packaging.build_config import build_output_dir, pyinstaller_work_dir


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "desktop_backend" / "packaging" / "desktop-backend.spec"


def main() -> int:
    dist_dir = build_output_dir(REPO_ROOT)
    work_dir = pyinstaller_work_dir(REPO_ROOT)
    shutil.rmtree(dist_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        str(SPEC_PATH),
    ]
    print(f"Building desktop sidecar for {platform.system()} -> {dist_dir}")
    subprocess.run(command, check=True, cwd=str(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```text
# requirements.txt
pyautogui==0.9.54
pyperclip==1.8.2
playwright>=1.40.0
beautifulsoup4>=4.12.2
lxml>=4.9.3
pillow>=10.1.0
markdownify>=1.2.0
pyinstaller
```

- [ ] **Step 5: Run the packaging contract test to verify it passes**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_sidecar_packaging -v`

Expected: PASS with `2 tests` and `OK`

- [ ] **Step 6: Commit the contract layer**

```bash
git add requirements.txt tests/test_desktop_sidecar_packaging.py desktop_backend/packaging/build_config.py desktop_backend/packaging/entrypoint.py desktop_backend/packaging/desktop-backend.spec scripts/build_desktop_sidecar.py
git commit -m "feat: add frozen desktop sidecar build pipeline"
```

### Task 2: Wire the sidecar artifact into Electron packaging

**Files:**
- Create: `desktop/scripts/build-sidecar.mjs`
- Modify: `desktop/package.json`
- Modify: `tests/test_desktop_sidecar_packaging.py`
- Test: `desktop/electron/backend/launch-spec.test.ts`

- [ ] **Step 1: Extend the failing contract test for Electron packaging**

```python
import json
from pathlib import Path


class DesktopSidecarPackagingTests(unittest.TestCase):
    def test_desktop_package_json_bundles_sidecar_resource(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        package_json = json.loads((repo_root / "desktop" / "package.json").read_text(encoding="utf-8"))
        extra_resources = package_json["build"].get("extraResources", [])
        self.assertIn(
            {
                "from": "../build/desktop-sidecar",
                "to": "sidecar",
                "filter": ["desktop-backend", "desktop-backend.exe"],
            },
            extra_resources,
        )
```

- [ ] **Step 2: Run the contract test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_sidecar_packaging -v`

Expected: FAIL because `extraResources` is missing from `desktop/package.json`

- [ ] **Step 3: Add an npm-side helper that reuses the active Python environment**

```javascript
// desktop/scripts/build-sidecar.mjs
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

function resolvePythonExecutable() {
  if (process.env.DESKTOP_BACKEND_PYTHON) return process.env.DESKTOP_BACKEND_PYTHON;
  if (process.env.CONDA_PREFIX) {
    const candidate = path.join(
      process.env.CONDA_PREFIX,
      process.platform === "win32" ? "python.exe" : path.join("bin", "python"),
    );
    if (fs.existsSync(candidate)) return candidate;
  }
  return process.platform === "win32" ? "python" : "python3";
}

const python = resolvePythonExecutable();
const script = path.resolve(process.cwd(), "..", "scripts", "build_desktop_sidecar.py");
const result = spawnSync(python, [script], {
  cwd: path.resolve(process.cwd(), ".."),
  stdio: "inherit",
  env: process.env,
});

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
```

- [ ] **Step 4: Update Electron package scripts and resource bundling**

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "build:desktop": "vite build",
    "build:sidecar": "node ./scripts/build-sidecar.mjs",
    "package:desktop": "npm run build:sidecar && npm run build && electron-builder --publish never",
    "package:desktop:dir": "npm run build:sidecar && npm run build && electron-builder --dir --publish never",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview",
    "test": "vitest run",
    "e2e": "npm run build && playwright test"
  },
  "build": {
    "appId": "com.wechat.scraper.desktop",
    "productName": "WeChatScraper",
    "directories": {
      "output": "release"
    },
    "files": ["dist/**", "dist-electron/**", "electron/**", "package.json"],
    "extraResources": [
      {
        "from": "../build/desktop-sidecar",
        "to": "sidecar",
        "filter": ["desktop-backend", "desktop-backend.exe"]
      }
    ],
    "asar": true
  }
}
```

- [ ] **Step 5: Re-run the tests for packaging and launch resolution**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_sidecar_packaging -v`

Expected: PASS with `OK`

Run: `npm --prefix desktop run test -- launch-spec.test.ts`

Expected: PASS with the existing packaged-sidecar resolution tests still green

- [ ] **Step 6: Commit the Electron integration**

```bash
git add desktop/package.json desktop/scripts/build-sidecar.mjs tests/test_desktop_sidecar_packaging.py
git commit -m "feat: bundle frozen sidecar into electron packages"
```

### Task 3: Update contributor docs and packaging guardrails

**Files:**
- Modify: `README.md`
- Modify: `docs/electron-desktop-ui.md`
- Modify: `tests/test_electron_only_repo.py`
- Test: `tests/test_electron_only_repo.py`

- [ ] **Step 1: Write a failing repo-docs test for the bundled-sidecar flow**

```python
class ElectronOnlyRepoTests(unittest.TestCase):
    def test_docs_describe_bundled_sidecar_packaging(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (REPO_ROOT / "docs" / "electron-desktop-ui.md").read_text(encoding="utf-8")
        required_snippets = (
            "frozen Python sidecar",
            "native platform",
            "resources/sidecar",
            "package:desktop",
        )
        for snippet in required_snippets:
            self.assertIn(snippet, readme)
            self.assertIn(snippet, release_notes)
```

- [ ] **Step 2: Run the doc contract test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`

Expected: FAIL because the docs do not yet describe bundled-sidecar packaging

- [ ] **Step 3: Update the README and release notes**

```text
README.md
## 打包说明
完整独立分发包需要先构建 frozen Python sidecar，再构建 Electron 包。当前支持的方式是各平台在各自平台本机构建。
conda run -n wechat-scraper python scripts/build_desktop_sidecar.py
npm --prefix desktop run package:desktop
- macOS 产物会把 `desktop-backend` 放入 `resources/sidecar/`
- Windows 产物会把 `desktop-backend.exe` 放入 `resources/sidecar/`
- `DESKTOP_BACKEND_EXECUTABLE` 仍可覆盖默认 sidecar 发现逻辑

docs/electron-desktop-ui.md
## Packaged App Behavior
- Native platform builds are the supported release path.
- Run `npm --prefix desktop run package:desktop` after the frozen sidecar build succeeds.
- Packaged builds include the frozen backend under `resources/sidecar/`.
- The packaged app should launch without Python installed on the destination machine.
```

- [ ] **Step 4: Re-run the repo-docs tests**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`

Expected: PASS with `OK`

- [ ] **Step 5: Commit the docs and guardrails**

```bash
git add README.md docs/electron-desktop-ui.md tests/test_electron_only_repo.py
git commit -m "docs: describe bundled sidecar packaging flow"
```

### Task 4: Verify the native packaging flow on the current platform

**Files:**
- Modify: none unless verification exposes a packaging defect
- Test: `tests/test_desktop_sidecar_packaging.py`
- Test: `desktop/electron/backend/launch-spec.test.ts`

- [ ] **Step 1: Build the frozen sidecar**

Run: `conda run -n wechat-scraper python scripts/build_desktop_sidecar.py`

Expected: exit `0` and an artifact under `build/desktop-sidecar/desktop-backend` on macOS or `build/desktop-sidecar/desktop-backend.exe` on Windows

- [ ] **Step 2: Package the Electron app without publishing**

Run: `npm --prefix desktop run package:desktop:dir`

Expected: exit `0` and an unpacked app under `desktop/release/`

- [ ] **Step 3: Run fast regression checks after packaging**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_sidecar_packaging tests.test_electron_only_repo -v`

Expected: PASS with `OK`

Run: `npm --prefix desktop run test -- launch-spec.test.ts`

Expected: PASS with the packaged-sidecar tests still green

- [ ] **Step 4: Commit any verification-driven fixes**

```bash
git add -A
git commit -m "test: verify bundled desktop sidecar packaging"
```
