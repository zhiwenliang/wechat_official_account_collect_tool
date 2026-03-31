import path from "node:path";

import { describe, expect, it } from "vitest";

import { resolveBackendLaunchSpec } from "./launch-spec";

describe("resolveBackendLaunchSpec", () => {
  const repositoryRoot = "/repo/root";
  const resourcesPath = "/app/resources";
  const defaultModule = "desktop_backend.app";

  it("uses DESKTOP_BACKEND_EXECUTABLE when the file exists", () => {
    const executable = "/opt/sidecar/desktop-backend";
    const spec = resolveBackendLaunchSpec(8765, {
      env: { DESKTOP_BACKEND_EXECUTABLE: executable },
      backendModule: defaultModule,
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
      backendModule: defaultModule,
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
        backendModule: defaultModule,
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
      backendModule: defaultModule,
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
      },
      backendModule: "my_backend.app",
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

  it("uses snapshotted backend module even if env DESKTOP_BACKEND_MODULE changes later", () => {
    const env: NodeJS.ProcessEnv = {
      DESKTOP_BACKEND_PYTHON: "/venv/bin/python",
      DESKTOP_BACKEND_MODULE: "initial.env.value",
    };
    const deps = {
      env,
      backendModule: "snapshotted.module",
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "linux" as const,
      existsSync: () => false,
    };

    expect(resolveBackendLaunchSpec(1, deps).args[1]).toBe("snapshotted.module");

    env.DESKTOP_BACKEND_MODULE = "mutated.env.value";
    expect(resolveBackendLaunchSpec(2, { ...deps, env }).args[1]).toBe("snapshotted.module");
  });

  it("selects packaged sidecar under resources when isPackaged and no python override", () => {
    const sidecarPath = path.join(resourcesPath, "sidecar", "desktop-backend");
    const spec = resolveBackendLaunchSpec(5000, {
      env: {},
      backendModule: defaultModule,
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === sidecarPath,
    });

    expect(spec.command).toBe(sidecarPath);
    expect(spec.cwd).toBe(path.dirname(sidecarPath));
  });

  it("prefers PyInstaller onedir binary under sidecar/desktop-backend/ when present", () => {
    const nestedPath = path.join(
      resourcesPath,
      "sidecar",
      "desktop-backend",
      "desktop-backend",
    );
    const legacyFlat = path.join(resourcesPath, "sidecar", "desktop-backend");
    const spec = resolveBackendLaunchSpec(5002, {
      env: {},
      backendModule: defaultModule,
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === nestedPath || candidate === legacyFlat,
      isExecutableFile: (candidate) => candidate === nestedPath,
    });

    expect(spec.command).toBe(nestedPath);
    expect(spec.cwd).toBe(path.dirname(nestedPath));
  });

  it("falls back to legacy onefile path when onedir binary is absent", () => {
    const legacyFlat = path.join(resourcesPath, "sidecar", "desktop-backend");
    const spec = resolveBackendLaunchSpec(5003, {
      env: {},
      backendModule: defaultModule,
      isPackaged: true,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === legacyFlat,
      isExecutableFile: (candidate) => candidate === legacyFlat,
    });

    expect(spec.command).toBe(legacyFlat);
  });

  it("falls back to resources root executable on darwin when sidecar dir is absent", () => {
    const fallback = path.join(resourcesPath, "desktop-backend");
    const spec = resolveBackendLaunchSpec(5001, {
      env: {},
      backendModule: defaultModule,
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
      backendModule: defaultModule,
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: () => false,
    });

    expect(spec.command).toBe("python3");
    expect(spec.args[0]).toBe("-m");
    expect(spec.args[1]).toBe(defaultModule);
    expect(spec.cwd).toBe(repositoryRoot);
  });

  it("resolves conda python when CONDA_PREFIX is set and binary exists", () => {
    const condaPython = path.join("/conda", "bin", "python");
    const spec = resolveBackendLaunchSpec(7000, {
      env: { CONDA_PREFIX: "/conda" },
      backendModule: defaultModule,
      isPackaged: false,
      resourcesPath,
      repositoryRoot,
      platform: "darwin",
      existsSync: (candidate) => candidate === condaPython,
    });

    expect(spec.command).toBe(condaPython);
  });
});
