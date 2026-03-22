import React from "react";
import { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api", () => ({
  getTaskSnapshot: vi.fn(),
  getStatistics: vi.fn(),
  startScrapeTask: vi.fn(),
  stopTask: vi.fn(),
}));

import { ScrapingPage } from "./ScrapingPage";
import { getTaskSnapshot, getStatistics, startScrapeTask } from "../../lib/api";

async function renderScrapingPage() {
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
        <ScrapingPage />
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

afterEach(async () => {
  document.body.innerHTML = "";
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("ScrapingPage", () => {
  it("starts a scraping task when the start button is clicked", async () => {
    vi.useFakeTimers();
    vi.mocked(getStatistics).mockResolvedValue({
      total: 0,
      pending: 0,
      scraped: 0,
      failed: 0,
      empty_content: 0,
      failed_urls: [],
    });
    vi.mocked(startScrapeTask).mockResolvedValue({ task_id: "scrape-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue({
      task_id: "scrape-1",
      task_type: "scrape",
      active: false,
      stopping: false,
      events: [],
    });

    const { container, root, client } = await renderScrapingPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="scrape-start"]');

    expect(startButton).not.toBeNull();

    await act(async () => {
      startButton?.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(startScrapeTask).toHaveBeenCalledTimes(1);

    await act(async () => {
      root.unmount();
      client.clear();
    });
  });

  it("renders scraping counters for pending, empty, success, and failure totals", async () => {
    vi.mocked(getStatistics).mockResolvedValue({
      total: 12,
      pending: 7,
      scraped: 3,
      failed: 2,
      empty_content: 4,
      failed_urls: [],
    });
    vi.mocked(startScrapeTask).mockResolvedValue({ task_id: "scrape-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue({
      task_id: "scrape-1",
      task_type: "scrape",
      active: true,
      stopping: false,
      events: [
        {
          type: "started",
          task_id: "scrape-1",
          task_type: "scrape",
        },
        {
          type: "progress",
          task_id: "scrape-1",
          current: 3,
          total: 10,
          message: "已处理 3/10 篇",
          success: 3,
          failed: 2,
        },
      ],
    });

    const { container, root, client } = await renderScrapingPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="scrape-start"]');

    if (!startButton) {
      throw new Error("expected scrape start button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("待抓取文章: 7 篇");
    expect(container.textContent).toContain("无内容文章: 4 篇");
    expect(container.textContent).toContain("成功: 3");
    expect(container.textContent).toContain("失败: 2");

    await act(async () => {
      root.unmount();
      client.clear();
    });
  });
});
