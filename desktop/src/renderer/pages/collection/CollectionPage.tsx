import { useEffect, useState } from "react";

import { TaskLogPanel } from "../../components/TaskLogPanel";
import { TaskProgressPanel } from "../../components/TaskProgressPanel";
import { getTaskSnapshot, startCollectionTask, stopTask } from "../../lib/api";
import type { TaskEvent, TaskSnapshotPayload } from "../../lib/task-events";
import { mergeTaskEvents, summarizeTaskProgress, summarizeTaskSession } from "../../lib/task-events";
const POLL_INTERVAL_MS = 1000;

function useCollectionTaskWorkflow() {
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
        setEvents((current) => mergeTaskEvents(current, nextSnapshot.events));

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
    setTaskId(null);
    setSnapshot(null);
    setEvents([]);
    setIsStarting(true);

    try {
      const result = await startCollectionTask();
      setTaskId(result.task_id);
    } catch (startError: unknown) {
      setError(startError instanceof Error ? startError.message : "采集任务启动失败");
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

export function CollectionPage() {
  const { taskId, events, summary, progress, error, start, stop, stopDisabled, startDisabled, snapshot } =
    useCollectionTaskWorkflow();

  return (
    <section className="shell__hero task-page" aria-label="Collection">
      <p className="shell__eyebrow">Collection</p>
      <h2>采集任务</h2>
      <p className="shell__description">
        在启动 Stage 1 之前，先确认 WeChat 桌面端已打开并完成坐标校准，避免鼠标自动化点错位置。
      </p>

      <div className="task-actions">
        <button name="collection-start" type="button" onClick={() => void start()} disabled={startDisabled}>
          开始采集
        </button>
        <button name="collection-stop" type="button" onClick={() => void stop()} disabled={stopDisabled}>
          停止任务
        </button>
      </div>

      <div className="task-grid">
        <section className="task-panel" aria-label="采集准备">
          <div className="task-panel__header">
            <h3>准备事项</h3>
            <p>仅保留 Tkinter 版本同等流程</p>
          </div>
          <ul className="guidance-list">
            <li>确认 WeChat 桌面端窗口处于前台。</li>
            <li>先完成校准，再启动采集任务。</li>
            <li>采集过程中不要移动鼠标或切换窗口。</li>
          </ul>
        </section>

        <section className="task-panel" aria-label="采集状态">
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
