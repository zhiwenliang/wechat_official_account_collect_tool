import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getBackendStatus } from "./lib/api";
import type { BackendStatus } from "./lib/task-events";
import { ArticlesPage } from "./pages/articles/ArticlesPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";

const INITIAL_STATUS: BackendStatus = {
  state: "starting",
  message: "正在启动 Python sidecar",
};
const BACKEND_STATUS_POLL_INTERVAL_MS = 3000;
const queryClient = new QueryClient();

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
    let intervalId: number | undefined;

    const refreshBackendStatus = async () => {
      try {
        const status = await getBackendStatus();
        if (isActive) {
          setBackendStatus(status);
        }
      } catch (error: unknown) {
        if (!isActive) {
          return;
        }

        setBackendStatus({
          state: "error",
          message: error instanceof Error ? error.message : "Desktop bridge unavailable",
        });
      }
    };

    void refreshBackendStatus();
    intervalId = window.setInterval(() => {
      void refreshBackendStatus();
    }, BACKEND_STATUS_POLL_INTERVAL_MS);

    return () => {
      isActive = false;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, []);

  const backendCopy = renderBackendCopy(backendStatus);
  const isBackendReady = backendStatus.state === "ready";

  return (
    <QueryClientProvider client={queryClient}>
      <main className="shell">
        <section className="shell__hero" aria-label="桌面工作区">
          <p className="shell__eyebrow">Electron Desktop Workspace</p>
          <h1>微信公众号文章采集工具</h1>
          <p className="shell__description">
            新桌面 UI 先接入只读总览和文章管理，后续再继续补采集、抓取和校准流程。
          </p>
        </section>

        <section className="shell__hero" aria-label="后端状态" role="status">
          <p className="shell__eyebrow">Python Sidecar</p>
          <h2>后端状态</h2>
          <p className="shell__description">{backendCopy.title}</p>
          <p className="shell__description">{backendCopy.description}</p>
        </section>

        <nav className="shell__nav" aria-label="主导航">
          <a href="#dashboard">概览</a>
          <a href="#articles">文章</a>
          <a href="#collect">采集</a>
          <a href="#scrape">抓取</a>
        </nav>
        {isBackendReady ? (
          <>
            <div id="dashboard">
              <DashboardPage />
            </div>
            <div id="articles">
              <ArticlesPage />
            </div>
          </>
        ) : (
          <section className="shell__hero" aria-label="页面加载状态">
            <p className="shell__eyebrow">Workspace</p>
            <h2>等待后端就绪</h2>
            <p className="shell__description">Python sidecar 就绪后再加载概览和文章页。</p>
          </section>
        )}
      </main>
    </QueryClientProvider>
  );
}
