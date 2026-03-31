import path from "node:path";

const BACKEND_HOST = "127.0.0.1";
const PACKAGED_SIDECAR_DIRNAME = "sidecar";
/** PyInstaller onedir output folder under resources/sidecar/. */
const PACKAGED_SIDECAR_BUNDLE_DIR = "desktop-backend";

export type BackendLaunchSpec = {
  command: string;
  args: string[];
  cwd: string;
  description: string;
};

export type ResolveBackendLaunchSpecDeps = {
  env: NodeJS.ProcessEnv;
  /** Snapshotted at main-process load (`process.env.DESKTOP_BACKEND_MODULE ?? "desktop_backend.app"`). */
  backendModule: string;
  isPackaged: boolean;
  resourcesPath: string;
  repositoryRoot: string;
  platform: NodeJS.Platform;
  existsSync: (filePath: string) => boolean;
  /**
   * When set (production), only regular files count as runnable sidecars. Required so onedir
   * layout (`.../sidecar/desktop-backend/` directory) does not shadow the real binary.
   */
  isExecutableFile?: (filePath: string) => boolean;
};

function packagedSidecarExecutableName(platform: NodeJS.Platform) {
  return platform === "win32" ? "desktop-backend.exe" : "desktop-backend";
}

function hasText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function resolvePythonCommand(deps: ResolveBackendLaunchSpecDeps) {
  const configuredPython = deps.env.DESKTOP_BACKEND_PYTHON;
  if (hasText(configuredPython)) {
    return configuredPython;
  }

  const condaPrefix = deps.env.CONDA_PREFIX;
  if (hasText(condaPrefix)) {
    const candidate = path.join(
      condaPrefix,
      deps.platform === "win32" ? "python.exe" : "bin/python",
    );
    if (deps.existsSync(candidate)) {
      return candidate;
    }
  }

  return deps.platform === "win32" ? "python" : "python3";
}

function resolveConfiguredWorkingDirectory(deps: ResolveBackendLaunchSpecDeps, defaultWorkingDirectory: string) {
  const configuredCwd = deps.env.DESKTOP_BACKEND_CWD;
  if (hasText(configuredCwd)) {
    return path.resolve(configuredCwd);
  }

  return defaultWorkingDirectory;
}

function packagedSidecarCandidatePaths(deps: ResolveBackendLaunchSpecDeps): string[] {
  const execName = packagedSidecarExecutableName(deps.platform);
  const sidecarRoot = path.join(deps.resourcesPath, PACKAGED_SIDECAR_DIRNAME);
  return [
    path.join(sidecarRoot, PACKAGED_SIDECAR_BUNDLE_DIR, execName),
    path.join(sidecarRoot, execName),
    path.join(deps.resourcesPath, execName),
  ];
}

function isRunnablePackagedBinary(deps: ResolveBackendLaunchSpecDeps, candidatePath: string): boolean {
  if (!deps.existsSync(candidatePath)) {
    return false;
  }

  if (deps.isExecutableFile === undefined) {
    return true;
  }

  return deps.isExecutableFile(candidatePath);
}

function resolvePackagedSidecarExecutable(deps: ResolveBackendLaunchSpecDeps) {
  const configuredExecutable = deps.env.DESKTOP_BACKEND_EXECUTABLE;
  if (hasText(configuredExecutable)) {
    const executablePath = path.resolve(configuredExecutable);
    if (!deps.existsSync(executablePath)) {
      throw new Error(`DESKTOP_BACKEND_EXECUTABLE points to a missing file: ${executablePath}`);
    }

    if (deps.isExecutableFile !== undefined && !deps.isExecutableFile(executablePath)) {
      throw new Error(`DESKTOP_BACKEND_EXECUTABLE must be a regular file: ${executablePath}`);
    }

    return executablePath;
  }

  const candidatePaths = packagedSidecarCandidatePaths(deps);

  for (const candidatePath of candidatePaths) {
    if (isRunnablePackagedBinary(deps, candidatePath)) {
      return candidatePath;
    }
  }

  throw new Error(
    `Packaged Python sidecar was not found. Expected one of: ${candidatePaths.join(
      ", ",
    )}. Set DESKTOP_BACKEND_EXECUTABLE to override or package the frozen backend into the resources directory.`,
  );
}

export function resolveBackendLaunchSpec(port: number, deps: ResolveBackendLaunchSpecDeps): BackendLaunchSpec {
  const commonArgs = ["--host", BACKEND_HOST, "--port", String(port)];
  const { backendModule } = deps;

  if (hasText(deps.env.DESKTOP_BACKEND_EXECUTABLE)) {
    const executable = resolvePackagedSidecarExecutable(deps);
    return {
      command: executable,
      args: commonArgs,
      cwd: resolveConfiguredWorkingDirectory(deps, path.dirname(executable)),
      description: `packaged sidecar at ${executable}`,
    };
  }

  if (hasText(deps.env.DESKTOP_BACKEND_PYTHON)) {
    const pythonCommand = resolvePythonCommand(deps);
    const cwd = resolveConfiguredWorkingDirectory(deps, deps.repositoryRoot);

    return {
      command: pythonCommand,
      args: ["-m", backendModule, ...commonArgs],
      cwd,
      description: `${pythonCommand} -m ${backendModule}`,
    };
  }

  if (deps.isPackaged) {
    const executable = resolvePackagedSidecarExecutable(deps);
    return {
      command: executable,
      args: commonArgs,
      cwd: resolveConfiguredWorkingDirectory(deps, path.dirname(executable)),
      description: `packaged sidecar at ${executable}`,
    };
  }

  const pythonCommand = resolvePythonCommand(deps);
  const cwd = resolveConfiguredWorkingDirectory(deps, deps.repositoryRoot);

  return {
    command: pythonCommand,
    args: ["-m", backendModule, ...commonArgs],
    cwd,
    description: `${pythonCommand} -m ${backendModule}`,
  };
}
