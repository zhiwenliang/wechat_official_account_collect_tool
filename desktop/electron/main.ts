import path from "node:path";

import { app, BrowserWindow } from "electron";

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL ?? "http://localhost:5173";

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

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
