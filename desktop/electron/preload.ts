import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("desktop", {
  getBackendStatus: () => ipcRenderer.invoke("desktop:get-backend-status"),
});
