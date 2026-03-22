import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

import { app, BrowserWindow, ipcMain } from "electron";

import type { BackendHealth, BackendStatus } from "../src/renderer/lib/task-events";

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://localhost:5173";
const BACKEND_HOST = "127.0.0.1";
const BACKEND_STARTUP_TIMEOUT_MS = 15000;

function getRepositoryRoot() {
  return path.resolve(__dirname, "..", "..");
}

function sleep(durationMs: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, durationMs);
  });
}

function formatErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function resolvePythonCommand() {
  if (process.env.DESKTOP_BACKEND_PYTHON) {
    return process.env.DESKTOP_BACKEND_PYTHON;
  }

  const condaPrefix = process.env.CONDA_PREFIX;
  if (condaPrefix) {
    const candidate = path.join(condaPrefix, process.platform === "win32" ? "python.exe" : "bin/python");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

function isBackendHealth(payload: unknown): payload is BackendHealth {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }

  const maybeHealth = payload as Record<string, unknown>;
  return maybeHealth.status === "ok" && typeof maybeHealth.service === "string";
}

async function reservePort(host: string) {
  return await new Promise<number>((resolve, reject) => {
    const server = net.createServer();

    server.unref();
    server.once("error", reject);
    server.listen(0, host, () => {
      const address = server.address();

      if (typeof address !== "object" || address === null) {
        reject(new Error("Unable to reserve a backend port"));
        return;
      }

      const { port } = address;
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve(port);
      });
    });
  });
}

class PythonSidecarController {
  private child: ChildProcess | null = null;

  private status: BackendStatus = {
    state: "starting",
    message: "正在启动 Python sidecar",
  };

  private startupPromise: Promise<void> | null = null;

  getStatus() {
    return this.status;
  }

  async start() {
    if (this.startupPromise) {
      return this.startupPromise;
    }

    this.startupPromise = this.bootstrap().catch((error: unknown) => {
      this.status = {
        state: "error",
        message: formatErrorMessage(error),
      };
      throw error;
    });

    return this.startupPromise;
  }

  stop() {
    if (this.child && !this.child.killed) {
      this.child.kill();
    }

    this.child = null;
    this.startupPromise = null;
  }

  private async bootstrap() {
    const port = await reservePort(BACKEND_HOST);
    const pythonCommand = resolvePythonCommand();
    const repositoryRoot = getRepositoryRoot();

    this.status = {
      state: "starting",
      message: `正在启动 Python sidecar: ${pythonCommand}`,
    };

    const child = spawn(
      pythonCommand,
      ["-m", "desktop_backend.app", "--host", BACKEND_HOST, "--port", String(port)],
      {
        cwd: repositoryRoot,
        env: {
          ...process.env,
          DESKTOP_BACKEND_PORT: String(port),
        },
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      },
    );

    this.child = child;

    child.stdout.on("data", (chunk) => {
      process.stdout.write(`[desktop-backend] ${chunk.toString()}`);
    });

    child.stderr.on("data", (chunk) => {
      process.stderr.write(`[desktop-backend] ${chunk.toString()}`);
    });

    child.once("exit", (code, signal) => {
      this.status = {
        state: "error",
        message: `Desktop backend exited (${describeExit(code, signal)})`,
      };
      this.child = null;
    });

    await this.waitForHealth(port);
  }

  private async waitForHealth(port: number) {
    const deadline = Date.now() + BACKEND_STARTUP_TIMEOUT_MS;
    const healthUrl = `http://${BACKEND_HOST}:${port}/health`;

    while (Date.now() < deadline) {
      if (this.child?.exitCode !== null) {
        throw new Error(
          this.status.state === "error"
            ? this.status.message
            : "Desktop backend exited before readiness",
        );
      }

      try {
        const response = await fetch(healthUrl);

        if (response.ok) {
          const payload = (await response.json()) as unknown;

          if (isBackendHealth(payload)) {
            this.status = {
              state: "ready",
              health: payload,
            };
            return;
          }
        }
      } catch {
        // Keep polling until the backend responds or the timeout expires.
      }

      await sleep(150);
    }

    throw new Error(`Timed out waiting for backend health at ${healthUrl}`);
  }
}

function describeExit(code: number | null, signal: NodeJS.Signals | null) {
  if (signal) {
    return `signal ${signal}`;
  }

  if (code !== null) {
    return `code ${code}`;
  }

  return "unknown exit";
}

const backend = new PythonSidecarController();

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 900,
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.setTitle("微信公众号文章采集工具");

  if (app.isPackaged) {
    window.loadFile(path.join(__dirname, "../dist/index.html"));
    return;
  }

  window.loadURL(DEV_SERVER_URL);
}

ipcMain.handle("desktop:get-backend-status", async () => backend.getStatus());

app.whenReady().then(async () => {
  try {
    await backend.start();
  } catch (error) {
    console.error("Desktop backend startup failed:", error);
  }

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  backend.stop();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
