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


if __name__ == "__main__":
    unittest.main()
