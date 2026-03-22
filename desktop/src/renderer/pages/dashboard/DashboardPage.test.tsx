import React from "react";
import { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "./DashboardPage";

function createJsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

async function renderDashboard() {
  const container = document.createElement("div");
  document.body.append(container);

  const client = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const root = createRoot(container);

  await act(async () => {
    root.render(
      <QueryClientProvider client={client}>
        <DashboardPage />
      </QueryClientProvider>,
    );
    await Promise.resolve();
  });

  return { container, root, client };
}

beforeAll(() => {
  (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
});

afterAll(() => {
  delete (globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT;
});

afterEach(() => {
  document.body.innerHTML = "";
  delete (window as typeof window & { desktop?: unknown }).desktop;
  vi.restoreAllMocks();
});

describe("DashboardPage", () => {
  it("renders statistics cards and recent articles from the desktop API", async () => {
    Object.defineProperty(window, "desktop", {
      configurable: true,
      value: {
        getBackendStatus: vi.fn().mockResolvedValue({
          state: "ready",
          baseUrl: "http://desktop-backend",
          health: {
            status: "ok",
            service: "desktop-backend",
          },
        }),
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url === "http://desktop-backend/api/statistics") {
          return Promise.resolve(
            createJsonResponse({
              total: 12,
              pending: 4,
              scraped: 6,
              failed: 1,
              empty_content: 1,
              failed_urls: [],
            }),
          );
        }

        if (url === "http://desktop-backend/api/recent-articles?limit=5") {
          return Promise.resolve(
            createJsonResponse([
              {
                id: 3,
                title: "Gamma",
                publish_time: "2024-01-03 08:00:00",
                status: "scraped",
                is_empty_content: 0,
              },
              {
                id: 2,
                title: "Beta",
                publish_time: "2024-01-02 08:00:00",
                status: "pending",
                is_empty_content: 0,
              },
            ]),
          );
        }

        return Promise.reject(new Error(`unexpected fetch: ${url}`));
      }),
    );

    const { container, root, client } = await renderDashboard();

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });

    expect(container.textContent).toContain("文章总数");
    expect(container.textContent).toContain("12");
    expect(container.textContent).toContain("待抓取");
    expect(container.textContent).toContain("最近文章");
    expect(container.textContent).toContain("Gamma");
    expect(container.textContent).toContain("Beta");

    await act(async () => {
      root.unmount();
      client.clear();
    });
  });
});
