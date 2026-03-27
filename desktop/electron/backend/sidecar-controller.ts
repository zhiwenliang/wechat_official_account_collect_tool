import { spawn, type ChildProcess } from "node:child_process";
import net from "node:net";

import type { BackendHealth, BackendStatus } from "../../src/shared/desktop-contract";
import { RetryableStartup } from "../retryable-startup";
import { resolveBackendLaunchSpec, type ResolveBackendLaunchSpecDeps } from "./launch-spec";

const BACKEND_HOST = "127.0.0.1";
const BACKEND_STARTUP_TIMEOUT_MS = 15000;

type SidecarProcess = ChildProcess & {
  stdout: NodeJS.ReadableStream;
  stderr: NodeJS.ReadableStream;
};

function formatErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function sleep(durationMs: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, durationMs);
  });
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

function describeExit(code: number | null, signal: NodeJS.Signals | null) {
  if (signal) {
    return `signal ${signal}`;
  }

  if (code !== null) {
    return `code ${code}`;
  }

  return "unknown exit";
}

export class PythonSidecarController {
  private child: SidecarProcess | null = null;

  private status: BackendStatus = {
    state: "starting",
    message: "正在启动 Python sidecar",
  };

  private startup = new RetryableStartup();

  constructor(private readonly getLaunchSpecDeps: () => ResolveBackendLaunchSpecDeps) {}

  getStatus() {
    return this.status;
  }

  async start() {
    return this.startup
      .run(async () => {
        await this.bootstrap();
      })
      .catch((error: unknown) => {
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
    const launchSpec = resolveBackendLaunchSpec(port, this.getLaunchSpecDeps());

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
          this.status.state === "error" ? this.status.message : "Desktop backend exited before readiness",
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
