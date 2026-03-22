import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

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
        health: {
          status: "ok",
          service: "desktop-backend",
        },
      }),
    ).toEqual({
      title: "已连接",
      description: "backend service: desktop-backend",
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
      description: "python not found",
    });
  });

  it("refreshes backend status after the initial ready snapshot", async () => {
    vi.useFakeTimers();
    const getBackendStatus = vi
      .fn()
      .mockResolvedValueOnce({
        state: "ready",
        health: {
          status: "ok",
          service: "desktop-backend",
        },
      })
      .mockResolvedValueOnce({
        state: "error",
        message: "desktop backend exited",
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
    expect(container.textContent).toContain("desktop backend exited");

    await act(async () => {
      root.unmount();
    });
  });
});
