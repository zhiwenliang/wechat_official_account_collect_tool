# Electron-Only Product Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the repository cutover to a strict Electron desktop product by removing stale CLI/Tkinter release paths, updating remaining backend copy, and rewriting docs around the Electron app only.

**Architecture:** The supported product surface stays `desktop/` plus the internal Python sidecar in `desktop_backend/`. The implementation does not rewrite scraper or storage logic; it removes obsolete repo assets and updates the remaining backend-facing copy and documentation so the repo consistently presents one supported launch path.

**Tech Stack:** Python 3.10, `unittest`, Electron, React, TypeScript, existing Python workflow/storage modules, GitHub Actions workflow files, Markdown docs.

---

## File Structure

- Create: `tests/test_electron_only_repo.py`
  - Repository-level guardrails that assert stale GUI/CLI packaging assets are gone and that user-facing docs no longer mention unsupported launch commands.
- Modify: `services/calibration_service.py`
  - Remove CLI-specific error/help text that still instructs users to run `python main.py ...`.
- Modify: `services/workflows.py`
  - Replace CLI next-step guidance with desktop-app wording.
- Modify: `scraper/link_collector.py`
  - Replace calibration error text that points users at the removed CLI.
- Modify: `README.md`
  - Rewrite setup, packaging, and troubleshooting around Electron-only usage.
- Modify: `docs/electron-desktop-ui.md`
  - Remove migration/fallback wording and describe the Electron app as the supported product.
- Modify: `AGENTS.md`
  - Update repository instructions so the documented project structure matches the Electron-only baseline.
- Modify: `CLAUDE.md`
  - Update contributor guidance to remove deleted entry points and obsolete packaging paths.
- Delete: `scripts/package_app.py`
  - Remove dead PyInstaller-based packaging script for the deleted GUI/CLI products.
- Delete: `.github/workflows/package-gui.yml`
  - Remove obsolete GitHub Actions workflow that packages the deleted Tkinter GUI.

### Task 1: Add Electron-Only Repository Guardrails

**Files:**
- Create: `tests/test_electron_only_repo.py`

- [ ] **Step 1: Write the failing repository audit test**

```python
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class ElectronOnlyRepoTests(unittest.TestCase):
    def test_legacy_packaging_assets_are_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "scripts" / "package_app.py").exists())
        self.assertFalse((REPO_ROOT / ".github" / "workflows" / "package-gui.yml").exists())

    def test_user_docs_do_not_advertise_removed_entrypoints(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (REPO_ROOT / "docs" / "electron-desktop-ui.md").read_text(encoding="utf-8")

        blocked_snippets = (
            "python main.py",
            "python -m gui.main",
            "Tkinter 回退",
            "package-gui.yml",
            "scripts/package_app.py",
        )

        for snippet in blocked_snippets:
            self.assertNotIn(snippet, readme)
            self.assertNotIn(snippet, release_notes)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: FAIL because `scripts/package_app.py`, `.github/workflows/package-gui.yml`, and current docs still exist or mention removed CLI/Tkinter flows.

- [ ] **Step 3: Create the repository audit test file**

```python
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class ElectronOnlyRepoTests(unittest.TestCase):
    def test_legacy_packaging_assets_are_removed(self) -> None:
        self.assertFalse((REPO_ROOT / "scripts" / "package_app.py").exists())
        self.assertFalse((REPO_ROOT / ".github" / "workflows" / "package-gui.yml").exists())

    def test_user_docs_do_not_advertise_removed_entrypoints(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (REPO_ROOT / "docs" / "electron-desktop-ui.md").read_text(encoding="utf-8")

        blocked_snippets = (
            "python main.py",
            "python -m gui.main",
            "Tkinter 回退",
            "package-gui.yml",
            "scripts/package_app.py",
        )

        for snippet in blocked_snippets:
            self.assertNotIn(snippet, readme)
            self.assertNotIn(snippet, release_notes)
```

- [ ] **Step 4: Run the test again and keep it failing for the right reason**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: FAIL only on the stale files/docs that the next tasks will remove.

- [ ] **Step 5: Commit**

```bash
git add tests/test_electron_only_repo.py
git commit -m "test: add electron-only repo audit coverage"
```

### Task 2: Remove Obsolete Packaging Paths and Fix Remaining User-Facing Copy

**Files:**
- Modify: `services/calibration_service.py`
- Modify: `services/workflows.py`
- Modify: `scraper/link_collector.py`
- Delete: `scripts/package_app.py`
- Delete: `.github/workflows/package-gui.yml`

- [ ] **Step 1: Write the failing backend copy regression tests**

Append tests like these to `tests/test_electron_only_repo.py`:

```python
    def test_backend_messages_do_not_reference_removed_cli(self) -> None:
        calibration_service = (REPO_ROOT / "services" / "calibration_service.py").read_text(encoding="utf-8")
        workflows = (REPO_ROOT / "services" / "workflows.py").read_text(encoding="utf-8")
        collector = (REPO_ROOT / "scraper" / "link_collector.py").read_text(encoding="utf-8")

        blocked_snippets = (
            "python main.py calibrate",
            "python main.py test",
            "python main.py scrape",
        )

        for snippet in blocked_snippets:
            self.assertNotIn(snippet, calibration_service)
            self.assertNotIn(snippet, workflows)
            self.assertNotIn(snippet, collector)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: FAIL because those strings still exist in the backend implementation files.

- [ ] **Step 3: Implement the minimal cutover changes**

Apply these concrete edits:

```python
# services/calibration_service.py
raise FileNotFoundError(f"配置文件不存在: {path}\n请先在桌面应用中完成坐标校准")

log("提示：可以在桌面应用的校准页面中运行校准测试")

# services/workflows.py
log("\n下一步: 返回桌面应用并开始抓取文章内容")

# scraper/link_collector.py
f"请先在桌面应用中完成坐标校准"
```

Delete the obsolete packaging assets entirely:

```text
Delete file: scripts/package_app.py
Delete file: .github/workflows/package-gui.yml
```

- [ ] **Step 4: Run the repository audit test to verify it passes**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/calibration_service.py services/workflows.py scraper/link_collector.py tests/test_electron_only_repo.py scripts/package_app.py .github/workflows/package-gui.yml
git commit -m "refactor: remove legacy packaging paths"
```

### Task 3: Rewrite Docs Around the Electron Product Only

**Files:**
- Modify: `README.md`
- Modify: `docs/electron-desktop-ui.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Extend the audit test to cover contributor docs**

Append this test to `tests/test_electron_only_repo.py`:

```python
    def test_repo_instructions_match_electron_only_product(self) -> None:
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        blocked_snippets = (
            "main.py",
            "python -m gui.main",
            "scripts/package_app.py",
            "Three UIs",
        )

        for snippet in blocked_snippets:
            self.assertNotIn(snippet, agents)
            self.assertNotIn(snippet, claude)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: FAIL because `README.md`, `docs/electron-desktop-ui.md`, `AGENTS.md`, and `CLAUDE.md` still describe removed CLI/Tkinter workflows.

- [ ] **Step 3: Rewrite the docs**

Use these concrete content changes:

```markdown
# README.md
- Replace the old "完整工作流程" section with Electron-first development and usage instructions.
- Keep contributor notes about `python -m desktop_backend.app`, but place them under a clearly labeled internal development section.
- Remove all `python main.py ...`, `python -m gui.main`, PyInstaller, and `package-gui.yml` references.
- Keep packaging instructions centered on:
  - `npm --prefix desktop install`
  - `npm --prefix desktop run dev`
  - `npm --prefix desktop run build`
  - `npm --prefix desktop run package:desktop`

# docs/electron-desktop-ui.md
- Replace migration language with release notes for the current supported product.
- Remove every mention of Tkinter fallback.
- Keep the sidecar resolution rules and startup-failure behavior.

# AGENTS.md
- Replace the project structure section so `desktop/` is the frontend entrypoint and `desktop_backend/` is the backend entrypoint.
- Replace the setup commands with Electron and sidecar development commands.
- Remove CLI- and Tkinter-specific testing guidance.

# CLAUDE.md
- Replace "Three UIs" with Electron-only architecture notes.
- Remove deleted CLI/Tkinter commands and PyInstaller packaging guidance.
- Keep internal notes about the Python sidecar and backend modules.
```

- [ ] **Step 4: Run the audit test to verify it passes**

Run: `conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/electron-desktop-ui.md AGENTS.md CLAUDE.md tests/test_electron_only_repo.py
git commit -m "docs: rewrite repository for electron-only product"
```

### Task 4: Run Product Verification and Clean Up Any Drift

**Files:**
- Modify: `tests/test_electron_only_repo.py` only if verification reveals a missed stale string

- [ ] **Step 1: Run the Python backend and repository test suite relevant to the supported product**

Run:

```bash
conda run -n wechat-scraper python -m unittest \
  tests.test_electron_only_repo \
  tests.test_desktop_backend_queries \
  tests.test_desktop_backend_server \
  tests.test_desktop_backend_tasks \
  tests.test_desktop_backend_import_export \
  tests.test_workflows \
  tests.test_file_store \
  tests.test_file_store_account_name \
  tests.test_database_account_name -v
```

Expected: PASS

- [ ] **Step 2: Run the desktop workspace checks**

Run:

```bash
npm --prefix desktop run typecheck
npm --prefix desktop run test
```

Expected: PASS

- [ ] **Step 3: Search for any remaining unsupported user-facing references**

Run:

```bash
rg -n "python main.py|python -m gui.main|Tkinter 回退|scripts/package_app.py|package-gui.yml" README.md docs AGENTS.md CLAUDE.md services scraper .github scripts
```

Expected: no matches

- [ ] **Step 4: Fix only the specific drift found during verification**

If a match remains, make the smallest possible targeted edit, for example:

```text
- Remove the stale string from the specific file.
- Re-run the exact failing command before broad re-verification.
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: verify electron-only cutover"
```
