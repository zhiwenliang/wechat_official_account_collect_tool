from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class DesktopSidecarPackagingTests(unittest.TestCase):
    def test_packaged_executable_basename_per_platform_contract(self) -> None:
        from desktop_backend.packaging import build_config

        cases = (
            ("darwin", "desktop-backend"),
            ("win32", "desktop-backend.exe"),
        )
        for platform, expected in cases:
            with self.subTest(platform=platform):
                self.assertEqual(
                    build_config.packaged_executable_basename(platform),
                    expected,
                )

    def test_packaged_executable_path_matches_resolver_layout(self) -> None:
        from desktop_backend.packaging import build_config

        self.assertEqual(
            build_config.packaged_executable_path(REPO_ROOT, "darwin"),
            REPO_ROOT
            / "build"
            / "desktop-sidecar"
            / "desktop-backend"
            / "desktop-backend",
        )
        self.assertEqual(
            build_config.packaged_executable_path(REPO_ROOT, "win32"),
            REPO_ROOT
            / "build"
            / "desktop-sidecar"
            / "desktop-backend"
            / "desktop-backend.exe",
        )

    def test_build_output_dir_is_repo_build_desktop_sidecar(self) -> None:
        from desktop_backend.packaging import build_config

        expected = REPO_ROOT / "build" / "desktop-sidecar"
        self.assertEqual(build_config.build_output_dir(REPO_ROOT), expected)

    def test_spec_is_onedir_with_collect(self) -> None:
        spec = (
            REPO_ROOT
            / "desktop_backend"
            / "packaging"
            / "desktop-backend.spec"
        )
        body = spec.read_text(encoding="utf-8")
        self.assertIn("COLLECT(", body)
        self.assertIn("exclude_binaries=True", body)
        self.assertIn("a.binaries", body)
        self.assertIn("a.zipfiles", body)
        self.assertIn("collect_submodules", body)
        self.assertIn("SIDECAR_SOURCE_PACKAGES", body)

    def test_packaging_spec_and_build_script_exist(self) -> None:
        spec = (
            REPO_ROOT
            / "desktop_backend"
            / "packaging"
            / "desktop-backend.spec"
        )
        self.assertTrue(
            spec.is_file(),
            msg=f"Expected PyInstaller spec at {spec}",
        )
        script = REPO_ROOT / "scripts" / "build_desktop_sidecar.py"
        self.assertTrue(
            script.is_file(),
            msg=f"Expected build script at {script}",
        )
        body = script.read_text(encoding="utf-8")
        self.assertIn("desktop-backend.spec", body)
        self.assertIn("build_output_dir", body)

    def test_desktop_package_json_extra_resources_sidecar_contract(self) -> None:
        pkg_path = REPO_ROOT / "desktop" / "package.json"
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        extra = pkg.get("build", {}).get("extraResources")
        self.assertIsInstance(extra, list, msg="build.extraResources must be a list")
        match = None
        for item in extra:
            if not isinstance(item, dict):
                continue
            if item.get("from") == "../build/desktop-sidecar" and item.get(
                "to",
            ) == "sidecar":
                match = item
                break
        self.assertIsNotNone(
            match,
            msg="Expected extraResources entry from ../build/desktop-sidecar to sidecar",
        )
        filt = match.get("filter")
        self.assertIsInstance(filt, list, msg="sidecar extraResources.filter must be a list")
        self.assertTrue(
            any("desktop-backend" in str(p) for p in filt),
            msg="extraResources must stage the PyInstaller onedir tree under desktop-backend/",
        )
        self.assertTrue(
            any("ms-playwright" in str(p) for p in filt),
            msg="extraResources must stage ms-playwright for Playwright browsers",
        )

    def test_playwright_staging_dir_contract(self) -> None:
        from desktop_backend.packaging import build_config

        self.assertEqual(
            build_config.playwright_staging_dir(REPO_ROOT),
            REPO_ROOT / "build" / "desktop-sidecar" / "ms-playwright",
        )

    def test_build_desktop_sidecar_script_stages_playwright(self) -> None:
        body = (REPO_ROOT / "scripts" / "build_desktop_sidecar.py").read_text(
            encoding="utf-8",
        )
        self.assertIn("stage_playwright_browsers", body)
        self.assertIn("PlaywrightBrowsersNotFoundError", body)

    def test_stage_playwright_browsers_copies_from_playwright_browsers_path(
        self,
    ) -> None:
        import os
        import tempfile

        from desktop_backend.packaging.playwright_stage import (
            stage_playwright_browsers,
        )

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "fake-ms-playwright"
            src.mkdir()
            (src / "chromium-4242").mkdir()
            (src / "firefox-999").mkdir()
            (src / "sentinel.txt").write_text("noise", encoding="utf-8")
            out = Path(tmp) / "dist"
            out.mkdir()
            old = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(src)
            try:
                dest = stage_playwright_browsers(out)
                self.assertEqual(
                    dest,
                    out / "ms-playwright",
                )
                self.assertTrue((dest / "chromium-4242").is_dir())
                self.assertFalse((dest / "firefox-999").exists())
                self.assertFalse((dest / "sentinel.txt").exists())
            finally:
                if old is None:
                    del os.environ["PLAYWRIGHT_BROWSERS_PATH"]
                else:
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = old

    def test_desktop_package_scripts_build_sidecar_before_electron_packaging(
        self,
    ) -> None:
        pkg_path = REPO_ROOT / "desktop" / "package.json"
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        scripts = pkg.get("scripts", {})
        for name in ("package:desktop", "package:desktop:dir"):
            with self.subTest(script=name):
                cmd = scripts.get(name, "")
                self.assertIn(
                    "build-sidecar.mjs",
                    cmd,
                    msg=f"{name} must invoke desktop/scripts/build-sidecar.mjs",
                )
                idx_sidecar = cmd.find("build-sidecar")
                idx_eb = cmd.find("electron-builder")
                self.assertNotEqual(idx_sidecar, -1)
                self.assertNotEqual(idx_eb, -1)
                self.assertLess(
                    idx_sidecar,
                    idx_eb,
                    msg=f"{name} must run sidecar build before electron-builder",
                )
                idx_vite = cmd.find("npm run build")
                self.assertNotEqual(idx_vite, -1)
                self.assertLess(
                    idx_vite,
                    idx_sidecar,
                    msg=f"{name} must run vite build before sidecar build",
                )

    def test_build_sidecar_mjs_conda_resolution_matches_e2e_pattern(self) -> None:
        """Guard against using CONDA_PREFIX alone (base env) for the interpreter."""
        body = (
            REPO_ROOT / "desktop" / "scripts" / "build-sidecar.mjs"
        ).read_text(encoding="utf-8")
        idx_explicit = body.find("DESKTOP_BACKEND_PYTHON")
        idx_default_env = body.find("CONDA_DEFAULT_ENV")
        idx_named_env = body.find("envs")
        self.assertNotEqual(idx_explicit, -1)
        self.assertNotEqual(idx_default_env, -1)
        self.assertNotEqual(idx_named_env, -1)
        self.assertNotEqual(body.find("wechat-scraper"), -1)
        self.assertLess(
            idx_explicit,
            idx_default_env,
            msg="Explicit python must be checked before Conda heuristics",
        )
        self.assertLess(
            idx_default_env,
            idx_named_env,
            msg="Active wechat-scraper check must precede envs/wechat-scraper path",
        )
        self.assertIn("desktop-smoke.spec.ts", body)

    def test_build_sidecar_mjs_includes_desktop_smoke_fallback_paths(self) -> None:
        body = (
            REPO_ROOT / "desktop" / "scripts" / "build-sidecar.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("USERPROFILE", body)
        self.assertIn(".conda", body)
        self.assertIn("python.exe", body)
        self.assertIn("miniconda3", body)
        self.assertIn("anaconda3", body)
        self.assertIn(
            "/opt/homebrew/anaconda3/envs/wechat-scraper/bin/python",
            body,
        )
        self.assertIn(
            "/opt/homebrew/Caskroom/miniconda/base/envs/"
            "wechat-scraper/bin/python",
            body,
        )
        self.assertIn(
            "/usr/local/Caskroom/miniconda/base/envs/"
            "wechat-scraper/bin/python",
            body,
        )
        idx_user = body.find("USERPROFILE")
        idx_unix = body.find("unixCandidates")
        idx_try = body.find("tryList")
        self.assertNotEqual(idx_user, -1)
        self.assertNotEqual(idx_unix, -1)
        self.assertNotEqual(idx_try, -1)
        self.assertLess(
            idx_user,
            idx_unix,
            msg="USERPROFILE .conda fallback must precede unixCandidates",
        )
        self.assertLess(
            idx_unix,
            idx_try,
            msg="unixCandidates must precede PATH probe (tryList)",
        )


if __name__ == "__main__":
    unittest.main()
