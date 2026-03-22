import { describe, expect, it } from "vitest";

import { mergeTaskEvents, summarizeTaskSession } from "./task-events";

describe("mergeTaskEvents", () => {
  it("appends only the new suffix when the backend snapshot contains the full history", () => {
    const started = {
      type: "started",
      task_id: "collection-1",
      task_type: "collection",
    } as const;
    const firstLog = {
      type: "log",
      task_id: "collection-1",
      message: "开始采集链接",
    } as const;
    const firstProgress = {
      type: "progress",
      task_id: "collection-1",
      current: 1,
      total: 3,
      message: "已采集 1/3 篇",
    } as const;
    const secondLog = {
      type: "log",
      task_id: "collection-1",
      message: "已保存: https://example.com/1",
    } as const;
    const secondProgress = {
      type: "progress",
      task_id: "collection-1",
      current: 2,
      total: 3,
      message: "已采集 2/3 篇",
    } as const;

    const firstSnapshot = [started, firstLog, firstProgress];
    const secondSnapshot = [started, firstLog, firstProgress, secondLog, secondProgress];

    const firstMerge = mergeTaskEvents([], firstSnapshot);
    const secondMerge = mergeTaskEvents(firstMerge, secondSnapshot);

    expect(firstMerge).toEqual(firstSnapshot);
    expect(secondMerge).toEqual(secondSnapshot);
  });

  it("reports stopped snapshots as the terminal stopped state", () => {
    expect(
      summarizeTaskSession({
        task_id: "collection-1",
        task_type: "collection",
        active: false,
        stopping: true,
        events: [
          {
            type: "started",
            task_id: "collection-1",
            task_type: "collection",
          },
          {
            type: "stopped",
            task_id: "collection-1",
            reason: "stop requested",
          },
        ],
      }),
    ).toEqual({
      title: "已停止",
      description: "stop requested",
    });
  });
});
