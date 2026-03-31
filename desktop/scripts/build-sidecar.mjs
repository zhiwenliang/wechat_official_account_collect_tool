/**
 * Build the frozen Python sidecar (PyInstaller) from the repo root.
 * Python resolution matches desktop/tests/e2e/desktop-smoke.spec.ts:
 * DESKTOP_BACKEND_PYTHON, then wechat-scraper via Conda (not raw base CONDA_PREFIX),
 * then the same fixed-path fallbacks as the E2E helper, then PATH.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(desktopRoot, "..");

function resolvePythonExecutable() {
  const explicit = process.env.DESKTOP_BACKEND_PYTHON?.trim();
  if (explicit) {
    return explicit;
  }

  const condaPrefix = process.env.CONDA_PREFIX?.trim();
  const win = process.platform === "win32";

  if (condaPrefix) {
    if (process.env.CONDA_DEFAULT_ENV === "wechat-scraper") {
      const active = win
        ? path.join(condaPrefix, "python.exe")
        : path.join(condaPrefix, "bin", "python");
      if (fs.existsSync(active)) {
        return active;
      }
    }

    const named = win
      ? path.join(condaPrefix, "envs", "wechat-scraper", "python.exe")
      : path.join(condaPrefix, "envs", "wechat-scraper", "bin", "python");
    if (fs.existsSync(named)) {
      return named;
    }
  }

  const userProfile = process.env.USERPROFILE?.trim();
  if (userProfile) {
    const candidate = path.join(
      userProfile,
      ".conda",
      "envs",
      "wechat-scraper",
      "python.exe",
    );
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  const unixCandidates = [
    path.join(
      process.env.HOME ?? "",
      "miniconda3",
      "envs",
      "wechat-scraper",
      "bin",
      "python",
    ),
    path.join(
      process.env.HOME ?? "",
      "anaconda3",
      "envs",
      "wechat-scraper",
      "bin",
      "python",
    ),
    "/opt/homebrew/anaconda3/envs/wechat-scraper/bin/python",
    "/opt/homebrew/Caskroom/miniconda/base/envs/wechat-scraper/bin/python",
    "/usr/local/Caskroom/miniconda/base/envs/wechat-scraper/bin/python",
  ];
  for (const candidate of unixCandidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }

  const tryList = process.platform === "win32" ? ["python"] : ["python3", "python"];
  for (const cmd of tryList) {
    const probe = spawnSync(cmd, ["-c", "import sys; print(sys.executable)"], {
      encoding: "utf8",
      shell: process.platform === "win32",
    });
    if (probe.status === 0 && probe.stdout?.trim()) {
      return probe.stdout.trim();
    }
  }

  throw new Error(
    "Could not resolve a Python interpreter. Set DESKTOP_BACKEND_PYTHON, install "
      + "conda env wechat-scraper (see desktop/tests/e2e/desktop-smoke.spec.ts), "
      + "or ensure python/python3 is on PATH.",
  );
}

function main() {
  const python = resolvePythonExecutable();
  const script = path.join(repoRoot, "scripts", "build_desktop_sidecar.py");
  if (!fs.existsSync(script)) {
    console.error(`Missing sidecar build script: ${script}`);
    process.exit(1);
  }

  const result = spawnSync(python, [script], {
    cwd: repoRoot,
    stdio: "inherit",
    env: process.env,
  });
  const code = result.status ?? 1;
  if (code !== 0) {
    process.exit(code);
  }
}

main();
