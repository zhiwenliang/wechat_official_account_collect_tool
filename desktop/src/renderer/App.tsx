import { useEffect, useState } from "react";

import { getBackendStatus } from "./lib/api";
import type { BackendStatus } from "./lib/task-events";

const INITIAL_STATUS: BackendStatus = {
  state: "starting",
  message: "正在启动 Python sidecar",
};

export function renderBackendCopy(status: BackendStatus) {
  switch (status.state) {
    case "starting":
      return {
        title: "启动中",
        description: status.message,
      };
    case "ready":
      return {
        title: "已连接",
        description: `backend service: ${status.health.service}`,
      };
    case "error":
      return {
        title: "启动失败",
        description: status.message,
      };
  }
}

export function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>(INITIAL_STATUS);

  useEffect(() => {
    let isActive = true;

    void getBackendStatus()
      .then((status) => {
        if (isActive) {
          setBackendStatus(status);
        }
      })
      .catch((error: unknown) => {
        if (!isActive) {
          return;
        }

        setBackendStatus({
          state: "error",
          message: error instanceof Error ? error.message : "Desktop bridge unavailable",
        });
      });

    return () => {
      isActive = false;
    };
  }, []);

  const backendCopy = renderBackendCopy(backendStatus);

  return (
    <main className="shell">
      <section className="shell__hero" aria-label="桌面工作区">
        <p className="shell__eyebrow">Electron Desktop Workspace</p>
        <h1>微信公众号文章采集工具</h1>
        <p className="shell__description">
          这是桌面端的导航壳层，后续阶段会把采集、抓取和索引能力接到这里。
        </p>
      </section>

      <section className="shell__hero" aria-label="后端状态" role="status">
        <p className="shell__eyebrow">Python Sidecar</p>
        <h2>后端状态</h2>
        <p className="shell__description">{backendCopy.title}</p>
        <p className="shell__description">{backendCopy.description}</p>
      </section>

      <nav className="shell__nav" aria-label="主导航">
        <a href="#collect">采集</a>
        <a href="#scrape">抓取</a>
        <a href="#index">索引</a>
        <a href="#settings">设置</a>
      </nav>
    </main>
  );
}
