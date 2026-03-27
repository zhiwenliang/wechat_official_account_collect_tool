import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

import { app, BrowserWindow, ipcMain } from "electron";

import type { BackendHealth, BackendStatus } from "../src/renderer/lib/task-events";
import { RetryableStartup } from "./retryable-startup";

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://localhost:5173";
const BACKEND_HOST = "127.0.0.1";
const BACKEND_STARTUP_TIMEOUT_MS = 15000;
const DEFAULT_BACKEND_MODULE = process.env.DESKTOP_BACKEND_MODULE ?? "desktop_backend.app";
const PACKAGED_SIDECAR_DIRNAME = "sidecar";
const PACKAGED_SIDECAR_EXECUTABLE_NAME = process.platform === "win32" ? "desktop-backend.exe" : "desktop-backend";
type SidecarProcess = ChildProcess & {
  stdout: NodeJS.ReadableStream;
  stderr: NodeJS.ReadableStream;
};

function getRepositoryRoot() {
  return path.resolve(__dirname, "..", "..");
}

function hasText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
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
  const configuredPython = process.env.DESKTOP_BACKEND_PYTHON;
  if (hasText(configuredPython)) {
    return configuredPython;
  }

  const condaPrefix = process.env.CONDA_PREFIX;
  if (hasText(condaPrefix)) {
    const candidate = path.join(condaPrefix, process.platform === "win32" ? "python.exe" : "bin/python");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return process.platform === "win32" ? "python" : "python3";
}

function resolveConfiguredWorkingDirectory(defaultWorkingDirectory: string) {
  const configuredCwd = process.env.DESKTOP_BACKEND_CWD;
  if (hasText(configuredCwd)) {
    return path.resolve(configuredCwd);
  }

  return defaultWorkingDirectory;
}

function resolvePackagedSidecarExecutable() {
  const configuredExecutable = process.env.DESKTOP_BACKEND_EXECUTABLE;
  if (hasText(configuredExecutable)) {
    const executablePath = path.resolve(configuredExecutable);
    if (!fs.existsSync(executablePath)) {
      throw new Error(`DESKTOP_BACKEND_EXECUTABLE points to a missing file: ${executablePath}`);
    }

    return executablePath;
  }

  const candidatePaths = [
    path.join(process.resourcesPath, PACKAGED_SIDECAR_DIRNAME, PACKAGED_SIDECAR_EXECUTABLE_NAME),
    path.join(process.resourcesPath, PACKAGED_SIDECAR_EXECUTABLE_NAME),
  ];

  for (const candidatePath of candidatePaths) {
    if (fs.existsSync(candidatePath)) {
      return candidatePath;
    }
  }

  throw new Error(
    `Packaged Python sidecar was not found. Expected one of: ${candidatePaths.join(
      ", ",
    )}. Set DESKTOP_BACKEND_EXECUTABLE to override or package the frozen backend into the resources directory.`,
  );
}

function resolveBackendLaunchSpec(port: number) {
  const commonArgs = ["--host", BACKEND_HOST, "--port", String(port)];

  if (hasText(process.env.DESKTOP_BACKEND_EXECUTABLE)) {
    const executable = resolvePackagedSidecarExecutable();
    return {
      command: executable,
      args: commonArgs,
      cwd: resolveConfiguredWorkingDirectory(path.dirname(executable)),
      description: `packaged sidecar at ${executable}`,
    };
  }

  if (hasText(process.env.DESKTOP_BACKEND_PYTHON)) {
    const pythonCommand = resolvePythonCommand();
    const cwd = resolveConfiguredWorkingDirectory(getRepositoryRoot());

    return {
      command: pythonCommand,
      args: ["-m", DEFAULT_BACKEND_MODULE, ...commonArgs],
      cwd,
      description: `${pythonCommand} -m ${DEFAULT_BACKEND_MODULE}`,
    };
  }

  if (app.isPackaged) {
    const executable = resolvePackagedSidecarExecutable();
    return {
      command: executable,
      args: commonArgs,
      cwd: resolveConfiguredWorkingDirectory(path.dirname(executable)),
      description: `packaged sidecar at ${executable}`,
    };
  }

  const pythonCommand = resolvePythonCommand();
  const cwd = resolveConfiguredWorkingDirectory(getRepositoryRoot());

  return {
    command: pythonCommand,
    args: ["-m", DEFAULT_BACKEND_MODULE, ...commonArgs],
    cwd,
    description: `${pythonCommand} -m ${DEFAULT_BACKEND_MODULE}`,
  };
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
  private child: SidecarProcess | null = null;

  private status: BackendStatus = {
    state: "starting",
    message: "正在启动 Python sidecar",
  };

  private startup = new RetryableStartup();

  getStatus() {
    return this.status;
  }

  async start() {
    return this.startup.run(async () => {
      await this.bootstrap();
    }).catch((error: unknown) => {
      this.status = {
        state: "error",
        message: formatErrorMessage(error),
      };
      throw error;
    });
  }

  stop() {
    if (this.child && !this.child.killed) {
      this.child.kill();
    }

    this.child = null;
    this.startup.reset();
  }

  private async bootstrap() {
    const port = await reservePort(BACKEND_HOST);
    const launchSpec = resolveBackendLaunchSpec(port);

    this.status = {
      state: "starting",
      message: `正在启动 Python sidecar: ${launchSpec.description}`,
    };

    const child = spawn(launchSpec.command, launchSpec.args, {
      cwd: launchSpec.cwd,
      env: {
        ...process.env,
        DESKTOP_BACKEND_PORT: String(port),
      },
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    }) as SidecarProcess;

    this.child = child;

    child.stdout.on("data", (chunk: Buffer) => {
      process.stdout.write(`[desktop-backend] ${chunk.toString()}`);
    });

    child.stderr.on("data", (chunk: Buffer) => {
      process.stderr.write(`[desktop-backend] ${chunk.toString()}`);
    });

    child.once("error", (error: Error) => {
      this.status = {
        state: "error",
        message: `Failed to start Python sidecar: ${formatErrorMessage(error)}`,
      };
      this.child = null;
    });

    child.once("exit", (code: number | null, signal: NodeJS.Signals | null) => {
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
              baseUrl: `http://${BACKEND_HOST}:${port}`,
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
    backgroundColor: "#f5f5f7",
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

app.whenReady().then(() => {
  createWindow();
  backend
    .start()
    .catch((error) => {
      console.error("Desktop backend startup failed:", error);
    });

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
