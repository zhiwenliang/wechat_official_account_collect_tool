import path from "node:path";

import { describe, expect, it } from "vitest";

import { resolveBackendLaunchSpec } from "./launch-spec";

describe("resolveBackendLaunchSpec", () => {
  const repositoryRoot = "/repo/root";
  const resourcesPath = "/app/resources";

  it("uses DESKTOP_BACKEND_EXECUTABLE when the file exists", () => {
    const executable = "/opt/sidecar/desktop-backend";
    const spec = resolveBackendLaunchSpec(8765, {
      env: { DESKTOP_BACKEND_EXECUTABLE: executable },
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === executable,
    });

    expect(spec.command).toBe(executable);
    expect(spec.args).toEqual(["--host", "127.0.0.1", "--port", "8765"]);
    expect(spec.cwd).toBe(path.dirname(executable));
    expect(spec.description).toContain(executable);
  });

  it("honors DESKTOP_BACKEND_CWD when launching a configured executable", () => {
    const executable = "/opt/sidecar/desktop-backend";
    const spec = resolveBackendLaunchSpec(1, {
      env: {
        DESKTOP_BACKEND_EXECUTABLE: executable,
        DESKTOP_BACKEND_CWD: "/custom/workdir",
      },
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === executable,
    });

    expect(spec.cwd).toBe(path.resolve("/custom/workdir"));
  });

  it("throws when DESKTOP_BACKEND_EXECUTABLE points to a missing file", () => {
    expect(() =>
      resolveBackendLaunchSpec(1, {
        env: { DESKTOP_BACKEND_EXECUTABLE: "/missing/desktop-backend" },
        isPackaged: false,
        resourcesPath,
        repositoryRoot,
        platform: "darwin",
        existsSync: () => false,
      }),
    ).toThrow(/missing file/);
  });

  it("prefers explicit DESKTOP_BACKEND_PYTHON over packaged and dev defaults", () => {
    const spec = resolveBackendLaunchSpec(3000, {
      env: { DESKTOP_BACKEND_PYTHON: "/usr/local/bin/python3" },
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: () => false,
    });

    expect(spec.command).toBe("/usr/local/bin/python3");
    expect(spec.args[0]).toBe("-m");
    expect(spec.args[1]).toBe("desktop_backend.app");
    expect(spec.args).toContain("--host");
    expect(spec.args).toContain("127.0.0.1");
    expect(spec.args).toContain("--port");
    expect(spec.args).toContain("3000");
    expect(spec.cwd).toBe(repositoryRoot);
  });

  it("uses DESKTOP_BACKEND_MODULE when provided for python -m launch", () => {
    const spec = resolveBackendLaunchSpec(4000, {
      env: {
        DESKTOP_BACKEND_PYTHON: "/venv/bin/python",
        DESKTOP_BACKEND_MODULE: "my_backend.app",
      },
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "linux",
      existsSync: () => false,
    });

    expect(spec.args).toEqual([
      "-m",
      "my_backend.app",
      "--host",
      "127.0.0.1",
      "--port",
      "4000",
    ]);
    expect(spec.description).toContain("my_backend.app");
  });

  it("selects packaged sidecar under resources when isPackaged and no python override", () => {
    const sidecarPath = path.join(resourcesPath, "sidecar", "desktop-backend");
    const spec = resolveBackendLaunchSpec(5000, {
      env: {},
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === sidecarPath,
    });

    expect(spec.command).toBe(sidecarPath);
    expect(spec.cwd).toBe(path.dirname(sidecarPath));
  });

  it("falls back to resources root executable on darwin when sidecar dir is absent", () => {
    const fallback = path.join(resourcesPath, "desktop-backend");
    const spec = resolveBackendLaunchSpec(5001, {
      env: {},
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === fallback,
    });

    expect(spec.command).toBe(fallback);
  });

  it("uses development python defaults when not packaged and no overrides", () => {
    const spec = resolveBackendLaunchSpec(6000, {
      env: {},
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: () => false,
    });

    expect(spec.command).toBe("python3");
    expect(spec.args[0]).toBe("-m");
    expect(spec.cwd).toBe(repositoryRoot);
  });

  it("resolves conda python when CONDA_PREFIX is set and binary exists", () => {
    const condaPython = path.join("/conda", "bin", "python");
    const spec = resolveBackendLaunchSpec(7000, {
      env: { CONDA_PREFIX: "/conda" },
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === condaPython,
    });

    expect(spec.command).toBe(condaPython);
  });
});
