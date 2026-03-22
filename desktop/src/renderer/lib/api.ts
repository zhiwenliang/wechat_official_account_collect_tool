import type { BackendStatus } from "./task-events";

export interface DesktopBridge {
  getBackendStatus: () => Promise<BackendStatus>;
}

declare global {
  interface Window {
    desktop?: DesktopBridge;
  }
}

export async function getBackendStatus(): Promise<BackendStatus> {
  if (!window.desktop) {
    throw new Error("Desktop bridge unavailable");
  }

  return window.desktop.getBackendStatus();
}
