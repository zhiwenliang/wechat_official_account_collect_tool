from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class PlaywrightStageResolutionTests(unittest.TestCase):
    def test_ms_playwright_root_from_chromium_executable_macos_style_layout(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            ms_playwright_root_from_chromium_executable,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ms = (
                root
                / "Library"
                / "Caches"
                / "ms-playwright"
                / "chromium-1208"
                / "chrome-mac-arm64"
            )
            ms.mkdir(parents=True)
            exe = ms / "Google Chrome for Testing"
            exe.write_bytes(b"")
            found = ms_playwright_root_from_chromium_executable(exe)
            expected = (root / "Library" / "Caches" / "ms-playwright").resolve()
            self.assertEqual(found, expected)

    def test_resolve_installed_prefers_playwright_browsers_path(self) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            env_dir = Path(tmp) / "from-env"
            env_dir.mkdir()
            (env_dir / "chromium-9999").mkdir()
            (env_dir / "marker").write_text("env", encoding="utf-8")
            old = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(env_dir)
            try:
                with patch("playwright.sync_api.sync_playwright") as mock_sync:
                    got = resolve_installed_playwright_browsers_dir()
                self.assertEqual(got, env_dir.resolve())
                mock_sync.assert_not_called()
            finally:
                if old is None:
                    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]
                else:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old

    def test_resolve_installed_uses_chromium_executable_path_without_env(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ms = (
                Path(tmp)
                / "Library"
                / "Caches"
                / "ms-playwright"
                / "chromium-9"
                / "chrome-mac-arm64"
            )
            ms.mkdir(parents=True)
            exe = ms / "Chrome"
            exe.write_bytes(b"")

            mock_p = MagicMock()
            mock_p.chromium.executable_path = str(exe)
            cm = MagicMock()
            cm.__enter__.return_value = mock_p
            cm.__exit__.return_value = None

            old = os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            try:
                with patch(
                    "playwright.sync_api.sync_playwright",
                    return_value=cm,
                ):
                    got = resolve_installed_playwright_browsers_dir()
            finally:
                if old is not None:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old

            expected = (
                Path(tmp) / "Library" / "Caches" / "ms-playwright"
            ).resolve()
            self.assertEqual(got, expected)

    @patch(
        "desktop_backend.packaging.playwright_stage."
        "resolve_via_playwright_chromium_executable",
        return_value=None,
    )
    @patch("sys.platform", "darwin")
    def test_resolve_installed_darwin_fallback_library_caches(
        self,
        _mock_pw: MagicMock,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "ms-playwright"
            cache.mkdir(parents=True)
            (cache / "chromium-100").mkdir()
            (cache / "x").write_text("y", encoding="utf-8")
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            old_pw = os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            try:
                got = resolve_installed_playwright_browsers_dir()
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
                if old_pw is not None:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old_pw

            self.assertEqual(got, cache.resolve())

    @patch(
        "desktop_backend.packaging.playwright_stage."
        "resolve_via_playwright_chromium_executable",
        return_value=None,
    )
    @patch("sys.platform", "linux")
    def test_resolve_installed_linux_fallback_dot_cache(
        self,
        _mock_pw: MagicMock,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / ".cache" / "ms-playwright"
            cache.mkdir(parents=True)
            (cache / "chromium-200").mkdir()
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            old_pw = os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            try:
                got = resolve_installed_playwright_browsers_dir()
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
                if old_pw is not None:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old_pw

            self.assertEqual(got, cache.resolve())

    def test_resolve_installed_rejects_env_path_without_chromium_revision_dir(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "ms-playwright"
            stale.mkdir()
            (stale / "empty-marker.txt").write_text("stale", encoding="utf-8")
            home = Path(tmp) / "userhome"
            home.mkdir()
            old = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
            old_home = os.environ.get("HOME")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(stale)
            os.environ["HOME"] = str(home)
            try:
                with patch(
                    "desktop_backend.packaging.playwright_stage."
                    "resolve_via_playwright_chromium_executable",
                    return_value=None,
                ):
                    with patch("sys.platform", "linux"):
                        got = resolve_installed_playwright_browsers_dir()
                self.assertIsNone(got)
            finally:
                if old is None:
                    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]
                else:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home

    def test_resolve_via_playwright_rejects_missing_executable_file(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_via_playwright_chromium_executable,
        )

        missing = Path("/nonexistent/path/to/chromium/binary")
        mock_p = MagicMock()
        mock_p.chromium.executable_path = str(missing)
        cm = MagicMock()
        cm.__enter__.return_value = mock_p
        cm.__exit__.return_value = None
        with patch("playwright.sync_api.sync_playwright", return_value=cm):
            self.assertIsNone(resolve_via_playwright_chromium_executable())

    def test_resolve_via_playwright_rejects_ms_playwright_without_chromium_dir(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_via_playwright_chromium_executable,
        )

        with tempfile.TemporaryDirectory() as tmp:
            ms = Path(tmp) / "ms-playwright"
            ms.mkdir()
            (ms / "firefox-123").mkdir()
            exe = ms / "fake" / "chrome"
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"")
            mock_p = MagicMock()
            mock_p.chromium.executable_path = str(exe)
            cm = MagicMock()
            cm.__enter__.return_value = mock_p
            cm.__exit__.return_value = None
            with patch("playwright.sync_api.sync_playwright", return_value=cm):
                self.assertIsNone(resolve_via_playwright_chromium_executable())

    @patch(
        "desktop_backend.packaging.playwright_stage."
        "resolve_via_playwright_chromium_executable",
        return_value=None,
    )
    @patch("sys.platform", "darwin")
    def test_resolve_installed_darwin_fallback_rejects_stale_cache_without_chromium(
        self,
        _mock_pw: MagicMock,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            resolve_installed_playwright_browsers_dir,
        )

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cache = home / "Library" / "Caches" / "ms-playwright"
            cache.mkdir(parents=True)
            (cache / "notes.txt").write_text("old", encoding="utf-8")
            old_home = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            old_pw = os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
            try:
                got = resolve_installed_playwright_browsers_dir()
            finally:
                if old_home is None:
                    del os.environ["HOME"]
                else:
                    os.environ["HOME"] = old_home
                if old_pw is not None:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old_pw

            self.assertIsNone(got)

    def test_stage_playwright_browsers_copies_only_chromium_related_top_level(
        self,
    ) -> None:
        from desktop_backend.packaging.playwright_stage import (
            stage_playwright_browsers,
        )

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "cache"
            src.mkdir()
            (src / "chromium-1").mkdir()
            (src / "chromium_headless_shell-2").mkdir()
            (src / "ffmpeg-3").mkdir()
            (src / "firefox-9").mkdir()
            (src / "webkit-8").mkdir()
            (src / "noise.txt").write_text("x", encoding="utf-8")
            out = Path(tmp) / "out"
            out.mkdir()
            old = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(src)
            try:
                dest = stage_playwright_browsers(out)
            finally:
                if old is None:
                    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]
                else:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old

            names = {p.name for p in dest.iterdir()}
            self.assertEqual(
                names,
                {"chromium-1", "chromium_headless_shell-2", "ffmpeg-3"},
            )

    def test_is_staged_ms_playwright_top_level_contract(self) -> None:
        from desktop_backend.packaging.playwright_stage import (
            is_staged_ms_playwright_top_level,
        )

        self.assertTrue(is_staged_ms_playwright_top_level("chromium-1200"))
        self.assertTrue(
            is_staged_ms_playwright_top_level("chromium_headless_shell-99"),
        )
        self.assertTrue(is_staged_ms_playwright_top_level("ffmpeg-1009"))
        self.assertFalse(is_staged_ms_playwright_top_level("firefox-1"))
        self.assertFalse(is_staged_ms_playwright_top_level("webkit-1"))


if __name__ == "__main__":
    unittest.main()
