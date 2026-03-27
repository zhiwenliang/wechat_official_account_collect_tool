import React from "react";
import { act } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("../../lib/api", () => ({
  getTaskSnapshot: vi.fn(),
  getCalibrationStatus: vi.fn().mockResolvedValue({}),
  respondToCalibrationTask: vi.fn(),
  startCalibrationTask: vi.fn(),
  stopTask: vi.fn(),
}));

import { CalibrationPage } from "./CalibrationPage";
import { getTaskSnapshot, respondToCalibrationTask, startCalibrationTask, stopTask } from "../../lib/api";
import type { TaskSnapshotPayload } from "../../lib/task-events";

type Snapshot = TaskSnapshotPayload;

function createSnapshot(overrides: Partial<Snapshot> = {}): Snapshot {
  return {
    task_id: "calibration-1",
    task_type: "calibration",
    active: true,
    stopping: false,
    prompt: null,
    events: [],
    ...overrides,
  };
}

async function renderCalibrationPage() {
  const container = document.createElement("div");
  document.body.append(container);

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const root = createRoot(container);

  await act(async () => {
    root.render(
      <QueryClientProvider client={client}>
        <CalibrationPage />
      </QueryClientProvider>,
    );
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

describe("CalibrationPage", () => {
  it("renders the active calibration prompt after starting an item", async () => {
    vi.useFakeTimers();
    vi.mocked(startCalibrationTask).mockResolvedValue({ task_id: "calibration-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        prompt: {
          kind: "position",
          step: "article_click_area.first_top",
          title: "文章点击位置",
          message: "步骤 1/3：请将鼠标移动到【任意一篇文章的顶部】。",
        },
        events: [
          {
            type: "started",
            task_id: "calibration-1",
            task_type: "calibration",
          },
        ],
      }),
    );

    const { container, root } = await renderCalibrationPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-article_click_area"]');

    if (!startButton) {
      throw new Error("expected article_click_area calibration button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toContain("文章点击位置");
    expect(container.textContent).toContain("步骤 1/3");
    expect(container.querySelector('button[name="calibration-prompt-record"]')).not.toBeNull();

    await act(async () => {
      root.unmount();
    });
  });

  it("maps the record button to a calibration task response", async () => {
    vi.useFakeTimers();
    vi.mocked(startCalibrationTask).mockResolvedValue({ task_id: "calibration-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        prompt: {
          kind: "position",
          step: "article_click_area.first_top",
          title: "文章点击位置",
          message: "步骤 1/3：请将鼠标移动到【任意一篇文章的顶部】。",
        },
      }),
    );
    vi.mocked(respondToCalibrationTask).mockResolvedValue({ task_id: "calibration-1", accepted: true });

    const { container, root } = await renderCalibrationPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-article_click_area"]');

    if (!startButton) {
      throw new Error("expected article_click_area calibration button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    const recordButton = container.querySelector<HTMLButtonElement>('button[name="calibration-prompt-record"]');

    if (!recordButton) {
      throw new Error("expected record prompt button");
    }

    await act(async () => {
      recordButton.click();
      await Promise.resolve();
    });

    // Advance through the 5-second countdown one tick at a time
    // (each tick requires React to re-render and schedule the next setTimeout)
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        vi.advanceTimersByTime(1000);
        await Promise.resolve();
      });
    }

    expect(respondToCalibrationTask).toHaveBeenCalledWith("calibration-1", { response: "record" });

    await act(async () => {
      root.unmount();
    });
  });

  it("maps confirmation responses to backend requests for the test flow", async () => {
    vi.useFakeTimers();
    vi.mocked(startCalibrationTask).mockResolvedValue({ task_id: "calibration-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        prompt: {
          kind: "confirm",
          step: "test.article_click_area",
          title: "校准测试",
          message: "鼠标位置是否在第一篇文章中间？",
          confirm_label: "是",
          reject_label: "否",
        },
      }),
    );
    vi.mocked(respondToCalibrationTask).mockResolvedValue({ task_id: "calibration-1", accepted: true });

    const { container, root } = await renderCalibrationPage();
    const testButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-test"]');

    if (!testButton) {
      throw new Error("expected calibration test button");
    }

    await act(async () => {
      testButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    const confirmButton = container.querySelector<HTMLButtonElement>('button[name="calibration-prompt-confirm-yes"]');

    if (!confirmButton) {
      throw new Error("expected confirm prompt button");
    }

    await act(async () => {
      confirmButton.click();
      await Promise.resolve();
    });

    expect(startCalibrationTask).toHaveBeenCalledWith("test");
    expect(respondToCalibrationTask).toHaveBeenCalledWith("calibration-1", { response: "confirm", accepted: true });

    await act(async () => {
      root.unmount();
    });
  });

  it("maps the cancel button to a stop request", async () => {
    vi.useFakeTimers();
    vi.mocked(startCalibrationTask).mockResolvedValue({ task_id: "calibration-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        prompt: {
          kind: "ack",
          step: "copy_link_menu.prepare",
          title: "复制链接菜单",
          message: "确认后将开始倒计时。",
        },
      }),
    );
    vi.mocked(stopTask).mockResolvedValue({ task_id: "calibration-1", stopping: true });

    const { container, root } = await renderCalibrationPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-copy_link_menu"]');

    if (!startButton) {
      throw new Error("expected copy_link_menu calibration button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    const cancelButton = container.querySelector<HTMLButtonElement>('button[name="calibration-prompt-cancel"]');

    if (!cancelButton) {
      throw new Error("expected cancel prompt button");
    }

    await act(async () => {
      cancelButton.click();
      await Promise.resolve();
    });

    expect(stopTask).toHaveBeenCalledWith("calibration-1");

    await act(async () => {
      root.unmount();
    });
  });

  it("keeps start buttons enabled after a failed restart from a completed calibration task", async () => {
    vi.useFakeTimers();
    const startTask = vi.mocked(startCalibrationTask);
    startTask
      .mockResolvedValueOnce({ task_id: "calibration-1" })
      .mockRejectedValueOnce(new Error("calibration unavailable"));
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        active: false,
        events: [
          {
            type: "started",
            task_id: "calibration-1",
            task_type: "calibration",
          },
          {
            type: "completed",
            task_id: "calibration-1",
            task_type: "calibration",
          },
        ],
      }),
    );

    const { container, root } = await renderCalibrationPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-article_click_area"]');

    if (!startButton) {
      throw new Error("expected article_click_area calibration button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(startTask).toHaveBeenCalledTimes(2);
    expect(startButton.disabled).toBe(false);

    await act(async () => {
      root.unmount();
    });
  });

  it("does not submit blank integer responses", async () => {
    vi.useFakeTimers();
    vi.mocked(startCalibrationTask).mockResolvedValue({ task_id: "calibration-1" });
    vi.mocked(getTaskSnapshot).mockResolvedValue(
      createSnapshot({
        prompt: {
          kind: "integer",
          step: "visible_articles.value",
          title: "可见文章数",
          message: "请输入当前窗口中同时可见的文章数量。",
          default_value: 5,
          min_value: 1,
        },
      }),
    );
    vi.mocked(respondToCalibrationTask).mockResolvedValue({ task_id: "calibration-1", accepted: true });

    const { container, root } = await renderCalibrationPage();
    const startButton = container.querySelector<HTMLButtonElement>('button[name="calibration-start-visible_articles"]');

    if (!startButton) {
      throw new Error("expected visible_articles calibration button");
    }

    await act(async () => {
      startButton.click();
      await Promise.resolve();
      await Promise.resolve();
    });

    const input = container.querySelector<HTMLInputElement>('input[type="number"]');
    const continueButton = container.querySelector<HTMLButtonElement>('button[name="calibration-prompt-continue"]');

    if (!input || !continueButton) {
      throw new Error("expected integer calibration controls");
    }

    await act(async () => {
      const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
      if (!valueSetter) {
        throw new Error("expected input value setter");
      }
      valueSetter.call(input, "");
      input.dispatchEvent(new Event("input", { bubbles: true }));
      await Promise.resolve();
    });

    expect(continueButton.disabled).toBe(true);

    await act(async () => {
      root.unmount();
    });
  });
});
