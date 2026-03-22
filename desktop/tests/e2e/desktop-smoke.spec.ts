import path from "node:path";
import fs from "node:fs";

import { expect, test } from "@playwright/test";
import { _electron as electron } from "playwright";

function resolvePythonExecutable() {
  if (process.env.DESKTOP_BACKEND_PYTHON) {
    return process.env.DESKTOP_BACKEND_PYTHON;
  }

  if (process.env.CONDA_PREFIX) {
    const candidate = path.join(
      process.env.CONDA_PREFIX,
      process.platform === "win32" ? "python.exe" : "bin/python",
    );
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  const userProfile = process.env.USERPROFILE;
  if (userProfile) {
    const candidate = path.join(userProfile, ".conda", "envs", "wechat-scraper", "python.exe");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

test("launches the sidecar and renders backend health through preload", async () => {
  const app = await electron.launch({
    args: [path.resolve(process.cwd(), "dist-electron", "main.js")],
    env: {
      ...process.env,
      VITE_DEV_SERVER_URL: "http://127.0.0.1:4173",
      DESKTOP_BACKEND_PYTHON: resolvePythonExecutable(),
    },
  });

  try {
    const window = await app.firstWindow();

    await expect(window.getByRole("status", { name: "后端状态" })).toContainText(
      "已连接",
      { timeout: 60000 },
    );
    await expect(window.getByText("desktop-backend")).toBeVisible();
  } finally {
    await app.close();
  }
});
