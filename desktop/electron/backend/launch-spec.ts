import path from "node:path";

const BACKEND_HOST = "127.0.0.1";
const PACKAGED_SIDECAR_DIRNAME = "sidecar";

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

function resolvePackagedSidecarExecutable(deps: ResolveBackendLaunchSpecDeps) {
  const configuredExecutable = deps.env.DESKTOP_BACKEND_EXECUTABLE;
  if (hasText(configuredExecutable)) {
    const executablePath = path.resolve(configuredExecutable);
    if (!deps.existsSync(executablePath)) {
      throw new Error(`DESKTOP_BACKEND_EXECUTABLE points to a missing file: ${executablePath}`);
    }

    return executablePath;
  }

  const execName = packagedSidecarExecutableName(deps.platform);
  const candidatePaths = [
    path.join(deps.resourcesPath, PACKAGED_SIDECAR_DIRNAME, execName),
    path.join(deps.resourcesPath, execName),
  ];

  for (const candidatePath of candidatePaths) {
    if (deps.existsSync(candidatePath)) {
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
