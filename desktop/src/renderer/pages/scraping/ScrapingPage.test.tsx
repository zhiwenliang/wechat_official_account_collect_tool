import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api", () => ({
  getTaskSnapshot: vi.fn(),
  startScrapeTask: vi.fn(),
  stopTask: vi.fn(),
}));

import { ScrapingPage } from "./ScrapingPage";
import { getTaskSnapshot, startScrapeTask } from "../../lib/api";

async function renderScrapingPage() {
  const container = document.createElement("div");
  document.body.append(container);

  const root = createRoot(container);

  await act(async () => {
    root.render(<ScrapingPage />);
    await Promise.resolve();
  });

  return { container, root };
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
    vi.mocked(startScrapeTask).mockResolvedValue({ task_id: "scrape-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue({
      task_id: "scrape-1",
      task_type: "scrape",
      active: false,
      stopping: false,
      events: [],
    });

    const { container, root } = await renderScrapingPage();
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
    });
  });
});
