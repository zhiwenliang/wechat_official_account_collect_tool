import fs from "node:fs";
import path from "node:path";

import { app, BrowserWindow, ipcMain } from "electron";

import { PythonSidecarController } from "./backend/sidecar-controller";
import { createMainWindow } from "./windows/create-main-window";

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://localhost:5173";
const DEFAULT_BACKEND_MODULE = process.env.DESKTOP_BACKEND_MODULE ?? "desktop_backend.app";

function getRepositoryRoot() {
  return path.resolve(__dirname, "..", "..");
}

const backend = new PythonSidecarController(() => ({
  env: process.env,
  backendModule: DEFAULT_BACKEND_MODULE,
  isPackaged: app.isPackaged,
  resourcesPath: process.resourcesPath,
  repositoryRoot: getRepositoryRoot(),
  platform: process.platform,
  existsSync: fs.existsSync.bind(fs),
}));

ipcMain.handle("desktop:get-backend-status", async () => backend.getStatus());

app.whenReady().then(() => {
  createMainWindow({
    preloadPath: path.join(__dirname, "preload.js"),
    packagedIndexHtmlPath: path.join(__dirname, "../dist/index.html"),
    devServerUrl: DEV_SERVER_URL,
  });

  backend.start().catch((error) => {
    console.error("Desktop backend startup failed:", error);
  });

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow({
        preloadPath: path.join(__dirname, "preload.js"),
        packagedIndexHtmlPath: path.join(__dirname, "../dist/index.html"),
        devServerUrl: DEV_SERVER_URL,
      });
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
