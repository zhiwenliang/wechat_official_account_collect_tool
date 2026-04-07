import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("./features/dashboard/DashboardPage", () => ({
  DashboardPage: () => <div>Dashboard stub</div>,
}));

vi.mock("./features/articles/ArticlesPage", () => ({
  ArticlesPage: () => <div>Articles stub</div>,
}));

vi.mock("./features/calibration/CalibrationPage", () => ({
  CalibrationPage: () => <div>Calibration stub</div>,
}));

vi.mock("./features/collection/CollectionPage", () => ({
  CollectionPage: () => <div>Collection stub</div>,
}));

vi.mock("./features/scraping/ScrapingPage", () => ({
  ScrapingPage: () => <div>Scraping stub</div>,
}));

import { App, renderBackendCopy } from "./App";

async function renderApp() {
  const container = document.createElement("div");
  document.body.append(container);

  const root = createRoot(container);

  await act(async () => {
    root.render(React.createElement(App));
    await Promise.resolve();
  });

  return { container, root };
}

afterEach(() => {
  document.body.innerHTML = "";
  delete (window as typeof window & { desktop?: unknown }).desktop;
  vi.restoreAllMocks();
  vi.useRealTimers();
});

beforeAll(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

afterAll(() => {
  delete (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT;
});

describe("renderBackendCopy", () => {
  it("describes a ready backend", () => {
    expect(
      renderBackendCopy({
        state: "ready",
        baseUrl: "http://desktop-backend",
        health: {
          status: "ok",
          service: "desktop-backend",
        },
      }),
    ).toEqual({
      title: "已连接",
      description: "服务运行正常",
    });
  });

  it("describes a backend startup failure", () => {
    expect(
      renderBackendCopy({
        state: "error",
        message: "python not found",
      }),
    ).toEqual({
      title: "启动失败",
      description: "服务启动失败，请重启应用",
    });
  });

  it("refreshes backend status after the initial ready snapshot", async () => {
    vi.useFakeTimers();
    let invocationCount = 0;
    const getBackendStatus = vi.fn().mockImplementation(() => {
      invocationCount += 1;
      if (invocationCount === 1) {
        return Promise.resolve({
          state: "ready",
          baseUrl: "http://desktop-backend",
          health: {
            status: "ok",
            service: "desktop-backend",
          },
        });
      }

      return Promise.resolve({
        state: "error",
        message: "desktop backend exited",
      });
    });

    Object.defineProperty(window, "desktop", {
      configurable: true,
      value: {
        getBackendStatus,
      },
    });

    const { container, root } = await renderApp();
    expect(container.textContent).toContain("已连接");

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
    });

    expect(container.textContent).toContain("启动失败");
    expect(container.textContent).toContain("服务启动失败，请重启应用");

    await act(async () => {
      root.unmount();
    });
  });

  it("does not mount data pages until the backend is ready", async () => {
    vi.useFakeTimers();
    let invocationCount = 0;
    const getBackendStatus = vi.fn().mockImplementation(() => {
      invocationCount += 1;
      if (invocationCount === 1) {
        return Promise.resolve({
          state: "starting",
          message: "正在初始化应用",
        });
      }

      return Promise.resolve({
        state: "ready",
        baseUrl: "http://desktop-backend",
        health: {
          status: "ok",
          service: "desktop-backend",
        },
      });
    });

    Object.defineProperty(window, "desktop", {
      configurable: true,
      value: {
        getBackendStatus,
      },
    });

    const { container, root } = await renderApp();
    expect(container.textContent).not.toContain("Dashboard stub");
    expect(container.textContent).not.toContain("Articles stub");
    expect(container.textContent).not.toContain("Calibration stub");
    expect(container.textContent).not.toContain("Collection stub");
    expect(container.textContent).not.toContain("Scraping stub");

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
    });

    expect(container.textContent).toContain("Dashboard stub");
    expect(container.textContent).toContain("Articles stub");
    expect(container.textContent).toContain("Calibration stub");
    expect(container.textContent).toContain("Collection stub");
    expect(container.textContent).toContain("Scraping stub");

    await act(async () => {
      root.unmount();
    });
  });
});
