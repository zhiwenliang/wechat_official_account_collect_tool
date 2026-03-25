import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Play, Square, CheckCircle, AlertTriangle } from "lucide-react";

import { TaskLogPanel } from "../../components/TaskLogPanel";
import { TaskProgressPanel } from "../../components/TaskProgressPanel";
import {
  getStatistics,
  getTaskSnapshot,
  startScrapeTask,
  stopTask,
} from "../../lib/api";
import type { TaskEvent, TaskSnapshotPayload } from "../../lib/task-events";
import {
  mergeTaskEvents,
  summarizeTaskProgress,
  summarizeTaskSession,
} from "../../lib/task-events";
import { cn } from "../../lib/utils";

const POLL_INTERVAL_MS = 1000;

function useScrapingTaskWorkflow() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<TaskSnapshotPayload | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    let cancelled = false;
    let intervalId: number | undefined;

    const syncTaskSnapshot = async () => {
      try {
        const nextSnapshot = await getTaskSnapshot(taskId);
        if (cancelled) {
          return;
        }

        setSnapshot(nextSnapshot);
        setEvents((current) =>
          mergeTaskEvents(current, nextSnapshot.events),
        );

        if (!nextSnapshot.active && intervalId !== undefined) {
          window.clearInterval(intervalId);
        }
      } catch (snapshotError: unknown) {
        if (cancelled) {
          return;
        }

        setError(
          snapshotError instanceof Error
            ? snapshotError.message
            : "任务状态加载失败",
        );
      }
    };

    void syncTaskSnapshot();
    intervalId = window.setInterval(() => {
      void syncTaskSnapshot();
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId !== undefined) {
        window.clearInterval(intervalId);
      }
    };
  }, [taskId]);

  const start = async () => {
    if (isStarting) {
      return;
    }

    setError(null);
    setTaskId(null);
    setSnapshot(null);
    setEvents([]);
    setIsStarting(true);

    try {
      const result = await startScrapeTask();
      setTaskId(result.task_id);
    } catch (startError: unknown) {
      setError(
        startError instanceof Error
          ? startError.message
          : "抓取任务启动失败",
      );
    } finally {
      setIsStarting(false);
    }
  };

  const stop = async () => {
    if (!taskId || isStopping) {
      return;
    }

    setIsStopping(true);
    setError(null);

    try {
      await stopTask(taskId);
    } catch (stopError: unknown) {
      setError(
        stopError instanceof Error ? stopError.message : "停止任务失败",
      );
    } finally {
      setIsStopping(false);
    }
  };

  const summary = summarizeTaskSession(snapshot, {
    isStarting,
    isStopping,
  });
  const progress = summarizeTaskProgress(events);
  const stopDisabled =
    !taskId || isStarting || isStopping || snapshot?.active !== true;
  const startDisabled =
    isStarting || (taskId !== null && snapshot?.active !== false);

  return {
    taskId,
    events,
    summary,
    progress,
    error,
    start,
    stop,
    stopDisabled,
    startDisabled,
    snapshot,
  };
}

export function ScrapingPage() {
  const {
    taskId,
    events,
    summary,
    progress,
    error,
    start,
    stop,
    stopDisabled,
    startDisabled,
    snapshot,
  } = useScrapingTaskWorkflow();
  const statisticsQuery = useQuery({
    queryKey: ["scraping-statistics"],
    queryFn: getStatistics,
  });
  const statistics = statisticsQuery.data ?? {
    total: 0,
    pending: 0,
    scraped: 0,
    failed: 0,
    empty_content: 0,
    failed_urls: [],
  };

  return (
    <section aria-label="Scraping" className="space-y-6">
      {/* Header + Actions */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">抓取任务</h1>
        <p className="mt-1 text-sm text-gray-500">
          Stage 2 会顺着数据库里的待抓取文章运行 Playwright，完成后自动生成
          Markdown 索引。
        </p>
      </div>

      <div className="task-actions flex flex-wrap gap-2">
        <button
          name="scrape-start"
          type="button"
          onClick={() => void start()}
          disabled={startDisabled}
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-blue-500 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 active:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play className="h-3.5 w-3.5" />
          开始抓取
        </button>
        <button
          name="scrape-stop"
          type="button"
          onClick={() => void stop()}
          disabled={stopDisabled}
          className="inline-flex h-9 items-center gap-2 rounded-lg border border-red-200 bg-white px-4 text-sm font-medium text-red-600 shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Square className="h-3.5 w-3.5" />
          停止任务
        </button>
      </div>

      {/* Info Cards */}
      <div className="task-grid grid gap-4 lg:grid-cols-2">
        <section
          className="rounded-xl border border-gray-200/80 bg-white p-5 shadow-card"
          aria-label="抓取准备"
        >
          <div className="task-panel__header">
            <h3 className="text-sm font-semibold text-gray-900">准备事项</h3>
          </div>
          <ul className="guidance-list mt-3 space-y-1.5 text-sm text-gray-600">
            <li className="flex items-start gap-2">
              <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
              确认数据库里有待抓取文章。
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-500" />
              确保 Chromium 和 Playwright 依赖已经准备好。
            </li>
            <li className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
              停止任务后会尽快释放浏览器资源。
            </li>
          </ul>
        </section>

        <section
          className="rounded-xl border border-gray-200/80 bg-white p-5 shadow-card"
          aria-label="抓取状态"
        >
          <div className="task-panel__header flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              当前任务状态
            </h3>
            <p className="text-xs text-gray-400">
              {taskId ? taskId : "等待启动"}
            </p>
          </div>
          <strong
            className={cn(
              "task-status-title mt-3 block text-2xl font-semibold",
              summary.title === "失败"
                ? "text-red-500"
                : summary.title === "已完成"
                  ? "text-green-600"
                  : "text-gray-900",
            )}
          >
            {summary.title}
          </strong>
          <p className="mt-1 text-sm text-gray-500">{summary.description}</p>
          {snapshot ? (
            <p className="task-status-meta mt-2 text-xs text-gray-400">
              {snapshot.active ? "任务仍在运行" : "任务已结束"}{" "}
              {snapshot.stopping ? "，正在停止" : ""}
            </p>
          ) : null}
          {error ? (
            <p className="task-status-error mt-2 text-xs text-red-500">
              {error}
            </p>
          ) : null}
        </section>
      </div>

      {/* Scraping Statistics */}
      <section
        className="task-panel task-counter-panel rounded-xl border border-gray-200/80 bg-white p-5 shadow-card"
        aria-label="抓取统计"
      >
        <div className="task-panel__header">
          <h3 className="text-sm font-semibold text-gray-900">抓取统计</h3>
        </div>
        <div className="task-counter-grid mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <article className="task-counter-card rounded-lg bg-gray-50 p-3">
            <p className="task-counter-card__label text-xs font-medium text-gray-500">
              待抓取文章: {statistics.pending} 篇
            </p>
          </article>
          <article className="task-counter-card rounded-lg bg-gray-50 p-3">
            <p className="task-counter-card__label text-xs font-medium text-gray-500">
              无内容文章: {statistics.empty_content} 篇
            </p>
          </article>
          <article className="task-counter-card rounded-lg bg-gray-50 p-3">
            <p className="task-counter-card__label text-xs font-medium text-green-600">
              成功: {progress.success ?? 0}
            </p>
          </article>
          <article className="task-counter-card rounded-lg bg-gray-50 p-3">
            <p className="task-counter-card__label text-xs font-medium text-red-500">
              失败: {progress.failed ?? 0}
            </p>
          </article>
        </div>
      </section>

      <div className="task-grid grid gap-4 lg:grid-cols-2">
        <TaskProgressPanel
          status={summary.title}
          current={progress.current}
          total={progress.total}
          message={progress.message}
        />
        <TaskLogPanel events={events} />
      </div>
    </section>
  );
}
