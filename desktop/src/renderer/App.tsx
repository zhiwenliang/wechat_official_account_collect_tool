import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  FileText,
  Crosshair,
  Download,
  Scissors,
  Circle,
} from "lucide-react";

import { getBackendStatus } from "./lib/api";
import { cn } from "./lib/utils";
import type { BackendStatus } from "./lib/task-events";
import { ArticlesPage } from "./pages/articles/ArticlesPage";
import { DashboardPage } from "./pages/dashboard/DashboardPage";
import { CalibrationPage } from "./pages/calibration/CalibrationPage";
import { CollectionPage } from "./pages/collection/CollectionPage";
import { ScrapingPage } from "./pages/scraping/ScrapingPage";

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

type Page = "dashboard" | "articles" | "calibration" | "collect" | "scrape";

const NAV_ITEMS: Array<{
  id: Page;
  label: string;
  icon: typeof LayoutDashboard;
}> = [
  { id: "dashboard", label: "概览", icon: LayoutDashboard },
  { id: "articles", label: "文章", icon: FileText },
  { id: "calibration", label: "校准", icon: Crosshair },
  { id: "collect", label: "采集", icon: Download },
  { id: "scrape", label: "抓取", icon: Scissors },
];

function BackendStatusDot({ status }: { status: BackendStatus }) {
  const color =
    status.state === "ready"
      ? "text-green-500"
      : status.state === "starting"
        ? "text-amber-400"
        : "text-red-500";
  const copy = renderBackendCopy(status);

  return (
    <div className="px-3 py-2 text-xs text-gray-500">
      <div className="flex items-center gap-2">
        <Circle className={cn("h-2.5 w-2.5 fill-current", color)} />
        <span className="truncate">{copy.title}</span>
      </div>
      {copy.description ? (
        <p className="mt-0.5 truncate pl-[18px] text-[11px] text-gray-400">
          {copy.description}
        </p>
      ) : null}
    </div>
  );
}

export function App() {
  const [backendStatus, setBackendStatus] =
    useState<BackendStatus>(INITIAL_STATUS);
  const [activePage, setActivePage] = useState<Page>("dashboard");

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
          message:
            error instanceof Error
              ? error.message
              : "Desktop bridge unavailable",
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

  const isBackendReady = backendStatus.state === "ready";

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen overflow-hidden bg-[#f5f5f7]">
        {/* ── Sidebar ── */}
        <aside className="flex w-52 flex-col border-r border-gray-200/80 bg-[#fbfbfd]">
          <div className="flex h-12 items-center px-4 pt-1 text-sm font-semibold text-gray-800 select-none"
               style={{ WebkitAppRegion: "drag" } as React.CSSProperties}>
            微信文章采集
          </div>

          <nav className="flex-1 space-y-0.5 px-2 pt-1" aria-label="主导航">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActivePage(item.id)}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition-colors",
                    isActive
                      ? "bg-gray-200/70 text-gray-900"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </button>
              );
            })}
          </nav>

          <div className="border-t border-gray-200/80 px-2 py-2">
            <BackendStatusDot status={backendStatus} />
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-5xl px-8 py-8">
            {isBackendReady ? (
              <>
                <div
                  id="dashboard"
                  className={activePage === "dashboard" ? "" : "hidden"}
                >
                  <DashboardPage />
                </div>
                <div
                  id="articles"
                  className={activePage === "articles" ? "" : "hidden"}
                >
                  <ArticlesPage />
                </div>
                <div
                  id="calibration"
                  className={activePage === "calibration" ? "" : "hidden"}
                >
                  <CalibrationPage />
                </div>
                <div
                  id="collect"
                  className={activePage === "collect" ? "" : "hidden"}
                >
                  <CollectionPage />
                </div>
                <div
                  id="scrape"
                  className={activePage === "scrape" ? "" : "hidden"}
                >
                  <ScrapingPage />
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-32 text-center">
                {backendStatus.state === "error" ? (
                  <>
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-red-50">
                      <Circle className="h-5 w-5 fill-red-400 text-red-400" />
                    </div>
                    <h2 className="text-lg font-semibold text-gray-800">
                      启动失败
                    </h2>
                    <p className="mt-1 text-sm text-gray-500">
                      {backendStatus.message}
                    </p>
                  </>
                ) : (
                  <>
                    <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
                    <h2 className="text-lg font-semibold text-gray-800">
                      等待后端就绪
                    </h2>
                    <p className="mt-1 text-sm text-gray-500">
                      Python sidecar 就绪后再加载页面
                    </p>
                  </>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </QueryClientProvider>
  );
}
