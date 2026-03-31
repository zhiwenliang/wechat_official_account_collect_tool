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

    def test_contributor_docs_do_not_reference_removed_desktop_backend_shims(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        combined = "\n".join((readme, agents, claude))

        removed_shim_paths = (
            "desktop_backend/task_handlers.py",
            "desktop_backend/tasks/handlers.py",
            "desktop_backend/tasks/registry.py",
            "desktop_backend/tasks/events.py",
            "desktop_backend/tasks/calibration_worker.py",
            "desktop_backend/query_handlers.py",
            "desktop_backend/schemas.py",
        )
        for path in removed_shim_paths:
            self.assertNotIn(path, combined, msg=f"Unexpected removed shim path reference: {path}")

    def test_contributor_docs_describe_bundled_sidecar_packaging(self) -> None:
        readme_raw = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        desktop_raw = (
            REPO_ROOT / "docs" / "electron-desktop-ui.md"
        ).read_text(encoding="utf-8")
        readme = readme_raw.lower()
        desktop_doc = desktop_raw.lower()
        required_phrases = (
            "frozen python sidecar",
            "native platform",
            "resources/sidecar",
            "package:desktop",
            "build:sidecar",
            "build_desktop_sidecar.py",
            "ms-playwright",
            "playwright install chromium",
            "playwright_browsers_path",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase, doc="README.md"):
                self.assertIn(phrase, readme)
            with self.subTest(
                phrase=phrase,
                doc="docs/electron-desktop-ui.md",
            ):
                self.assertIn(phrase, desktop_doc)
        self.assertIn("DESKTOP_BACKEND_EXECUTABLE", readme_raw)
        self.assertIn("DESKTOP_BACKEND_EXECUTABLE", desktop_raw)
        self.assertIn("开发与调试", readme_raw)
        self.assertIn("非最终用户", readme_raw)
        self.assertIn("python -m desktop_backend.app", readme)
        self.assertIn("python -m desktop_backend.app", desktop_doc)
        self.assertIn("development", desktop_doc)
        self.assertIn("debug", desktop_doc)


if __name__ == "__main__":
    unittest.main()
