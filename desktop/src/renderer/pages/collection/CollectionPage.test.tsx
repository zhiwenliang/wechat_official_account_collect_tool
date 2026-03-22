import React from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api", () => ({
  getTaskSnapshot: vi.fn(),
  startCollectionTask: vi.fn(),
  stopTask: vi.fn(),
}));

import { CollectionPage } from "./CollectionPage";
import { getTaskSnapshot, startCollectionTask, stopTask } from "../../lib/api";
import type { TaskSnapshotPayload } from "../../lib/task-events";

type Snapshot = TaskSnapshotPayload;

function createSnapshot(overrides: Partial<Snapshot> = {}): Snapshot {
  return {
    task_id: "collection-1",
    task_type: "collection",
    active: true,
    stopping: false,
    events: [],
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((value) => {
    resolve = value;
  });
  return { promise, resolve };
}

async function renderCollectionPage() {
  const container = document.createElement("div");
  document.body.append(container);

  const root = createRoot(container);

  await act(async () => {
    root.render(<CollectionPage />);
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

describe("CollectionPage", () => {
  it("starts a collection task when the start button is clicked", async () => {
    vi.useFakeTimers();
    vi.mocked(startCollectionTask).mockResolvedValue({ task_id: "collection-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        active: false,
        events: [
          {
            type: "started",
            task_id: "collection-1",
            task_type: "collection",
          },
        ],
      }),
    );

    const { container, root } = await renderCollectionPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="collection-start"]');

    expect(startButton).not.toBeNull();

    await act(async () => {
      startButton?.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(startCollectionTask).toHaveBeenCalledTimes(1);

    await act(async () => {
      root.unmount();
    });
  });

  it("appends task events into the progress and log panels as snapshots arrive", async () => {
    vi.useFakeTimers();
    vi.mocked(startCollectionTask).mockResolvedValue({ task_id: "collection-1" });

    let callCount = 0;
    vi.mocked(getTaskSnapshot).mockImplementation(async () => {
      callCount += 1;
      if (callCount === 1) {
        return createSnapshot({
          events: [
            {
              type: "started",
              task_id: "collection-1",
              task_type: "collection",
            },
            {
              type: "log",
              task_id: "collection-1",
              message: "开始采集链接",
            },
            {
              type: "progress",
              task_id: "collection-1",
              current: 1,
              total: 3,
              message: "已采集 1/3 篇",
            },
          ],
        });
      }

      if (callCount === 2) {
        return createSnapshot({
          events: [
            {
              type: "log",
              task_id: "collection-1",
              message: "已保存: https://example.com/1",
            },
            {
              type: "progress",
              task_id: "collection-1",
              current: 2,
              total: 3,
              message: "已采集 2/3 篇",
            },
          ],
        });
      }

      return createSnapshot({
        active: false,
        events: [
          {
            type: "completed",
            task_id: "collection-1",
            task_type: "collection",
          },
        ],
      });
    });

    const { container, root } = await renderCollectionPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="collection-start"]');

    if (!startButton) {
      throw new Error("expected collection start button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("开始采集链接");
    expect(container.textContent).toContain("任务进度");
    expect(container.textContent).toContain("1 / 3");

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("已保存: https://example.com/1");
    expect(container.textContent).toContain("2 / 3");

    await act(async () => {
      root.unmount();
    });
  });

  it("disables the stop button while the stop request is in flight", async () => {
    vi.useFakeTimers();
    vi.mocked(startCollectionTask).mockResolvedValue({ task_id: "collection-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        events: [
          {
            type: "started",
            task_id: "collection-1",
            task_type: "collection",
          },
        ],
      }),
    );

    const pendingStop = deferred<{ task_id: string; stopping: boolean }>();
    vi.mocked(stopTask).mockReturnValue(pendingStop.promise);

    const { container, root } = await renderCollectionPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="collection-start"]');

    if (!startButton) {
      throw new Error("expected collection start button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    const stopButton = container.querySelector<HTMLButtonElement>('button[name="collection-stop"]');

    if (!stopButton) {
      throw new Error("expected collection stop button");
    }

    await act(async () => {
      stopButton.click();
      await Promise.resolve();
    });

    expect(stopButton.disabled).toBe(true);
    expect(stopTask).toHaveBeenCalledWith("collection-1");

    await act(async () => {
      pendingStop.resolve({ task_id: "collection-1", stopping: true });
      await Promise.resolve();
    });

    await act(async () => {
      root.unmount();
    });
  });
});
