import { app, BrowserWindow } from "electron";

export type CreateMainWindowOptions = {
  preloadPath: string;
  packagedIndexHtmlPath: string;
  devServerUrl: string;
};

export function createMainWindow(options: CreateMainWindowOptions) {
  const window = new BrowserWindow({
    width: 1280,
    height: 900,
    backgroundColor: "#f5f5f7",
    webPreferences: {
      preload: options.preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.setTitle("微信公众号文章采集工具");

  if (app.isPackaged) {
    window.loadFile(options.packagedIndexHtmlPath);
    return;
  }

  window.loadURL(options.devServerUrl);
}
