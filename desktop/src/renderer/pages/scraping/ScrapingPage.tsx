import { useEffect, useState } from "react";

import { TaskLogPanel } from "../../components/TaskLogPanel";
import { TaskProgressPanel } from "../../components/TaskProgressPanel";
import { getTaskSnapshot, startScrapeTask, stopTask } from "../../lib/api";
import type { TaskEvent, TaskSnapshotPayload } from "../../lib/task-events";
import { summarizeTaskProgress, summarizeTaskSession } from "../../lib/task-events";
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
        setEvents((current) => current.concat(nextSnapshot.events));

        if (!nextSnapshot.active && intervalId !== undefined) {
          window.clearInterval(intervalId);
        }
      } catch (snapshotError: unknown) {
        if (cancelled) {
          return;
        }

        setError(snapshotError instanceof Error ? snapshotError.message : "任务状态加载失败");
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
    setSnapshot(null);
    setEvents([]);
    setIsStarting(true);

    try {
      const result = await startScrapeTask();
      setTaskId(result.task_id);
    } catch (startError: unknown) {
      setError(startError instanceof Error ? startError.message : "抓取任务启动失败");
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
      setError(stopError instanceof Error ? stopError.message : "停止任务失败");
    } finally {
      setIsStopping(false);
    }
  };

  const summary = summarizeTaskSession(snapshot, {
    isStarting,
    isStopping,
  });
  const progress = summarizeTaskProgress(events);
  const stopDisabled = !taskId || isStarting || isStopping || snapshot?.active !== true;
  const startDisabled = isStarting || (taskId !== null && snapshot?.active !== false);

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
  const { taskId, events, summary, progress, error, start, stop, stopDisabled, startDisabled, snapshot } =
    useScrapingTaskWorkflow();

  return (
    <section className="shell__hero task-page" aria-label="Scraping">
      <p className="shell__eyebrow">Scraping</p>
      <h2>抓取任务</h2>
      <p className="shell__description">
        Stage 2 会顺着数据库里的待抓取文章运行 Playwright，完成后自动生成 Markdown 索引。
      </p>

      <div className="task-actions">
        <button name="scrape-start" type="button" onClick={() => void start()} disabled={startDisabled}>
          开始抓取
        </button>
        <button name="scrape-stop" type="button" onClick={() => void stop()} disabled={stopDisabled}>
          停止任务
        </button>
      </div>

      <div className="task-grid">
        <section className="task-panel" aria-label="抓取准备">
          <div className="task-panel__header">
            <h3>准备事项</h3>
            <p>继续沿用桌面端流程</p>
          </div>
          <ul className="guidance-list">
            <li>确认数据库里有待抓取文章。</li>
            <li>确保 Chromium 和 Playwright 依赖已经准备好。</li>
            <li>停止任务后会尽快释放浏览器资源。</li>
          </ul>
        </section>

        <section className="task-panel" aria-label="抓取状态">
          <div className="task-panel__header">
            <h3>当前任务状态</h3>
            <p>{taskId ? taskId : "等待启动"}</p>
          </div>
          <strong className="task-status-title">{summary.title}</strong>
          <p className="shell__description">{summary.description}</p>
          {snapshot ? (
            <p className="task-status-meta">
              {snapshot.active ? "任务仍在运行" : "任务已结束"} {snapshot.stopping ? "，正在停止" : ""}
            </p>
          ) : null}
          {error ? <p className="task-status-error">{error}</p> : null}
        </section>
      </div>

      <div className="task-grid">
        <TaskProgressPanel status={summary.title} current={progress.current} total={progress.total} message={progress.message} />
        <TaskLogPanel events={events} />
      </div>
    </section>
  );
}
