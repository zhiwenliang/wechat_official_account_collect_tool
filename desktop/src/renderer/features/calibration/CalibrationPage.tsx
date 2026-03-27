import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Play, Square, Crosshair, CheckCircle2 } from "lucide-react";

import { TaskLogPanel } from "../../components/TaskLogPanel";
import {
  getTaskSnapshot,
  getCalibrationStatus,
  respondToCalibrationTask,
  startCalibrationTask,
  stopTask,
  type CalibrationAction,
} from "../../lib/api";
import type {
  TaskEvent,
  TaskPrompt,
  TaskSnapshotPayload,
} from "../../lib/task-events";
import { mergeTaskEvents, summarizeTaskSession } from "../../lib/task-events";
import { cn } from "../../lib/utils";

const CALIBRATION_POLL_INTERVAL_MS = 1000;

const CALIBRATION_ITEMS: Array<{
  action: CalibrationAction;
  title: string;
  description: string;
}> = [
  {
    action: "article_click_area",
    title: "文章点击位置",
    description: "记录文章列表点击点和行高。",
  },
  {
    action: "scroll_amount",
    title: "滚动单位",
    description: "根据参考点计算每次滚动一行所需的单位。",
  },
  {
    action: "visible_articles",
    title: "可见文章数",
    description: "设置当前窗口同时可见的文章数量。",
  },
  {
    action: "more_button",
    title: "更多按钮",
    description: "记录微信内置浏览器右上角更多按钮坐标。",
  },
  {
    action: "copy_link_menu",
    title: "复制链接菜单",
    description: "通过倒计时记录复制链接菜单项位置。",
  },
  {
    action: "tab_management",
    title: "标签管理",
    description: "自动打开标签后记录第一个标签和关闭按钮位置。",
  },
];

function useCalibrationTaskWorkflow() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<TaskSnapshotPayload | null>(null);
  const [events, setEvents] = useState<TaskEvent[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [isResponding, setIsResponding] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [selectedAction, setSelectedAction] =
    useState<CalibrationAction | null>(null);

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

        if (!nextSnapshot.active) {
          setIsStopping(false);
          setIsResponding(false);
          if (intervalId !== undefined) {
            window.clearInterval(intervalId);
            intervalId = undefined;
          }
        }
      } catch (_error: unknown) {
        if (!cancelled) {
          setIsStopping(false);
          setIsResponding(false);
        }
      }
    };

    void syncTaskSnapshot();
    intervalId = window.setInterval(() => {
      void syncTaskSnapshot();
    }, CALIBRATION_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [taskId]);

  const startAction = async (action: CalibrationAction) => {
    setIsStarting(true);
    setIsStopping(false);
    setIsResponding(false);
    setTaskId(null);
    setSnapshot(null);
    setEvents([]);
    setSelectedAction(action);

    try {
      const result = await startCalibrationTask(action);
      setTaskId(result.task_id);
    } catch (_error: unknown) {
      setTaskId(null);
    } finally {
      setIsStarting(false);
    }
  };

  const respond = async (
    payload:
      | { response: "record" }
      | { response: "continue"; value?: number }
      | { response: "confirm"; accepted: boolean },
  ) => {
    if (!taskId) {
      return;
    }

    setIsResponding(true);
    try {
      await respondToCalibrationTask(taskId, payload);
    } finally {
      setIsResponding(false);
    }
  };

  const cancel = async () => {
    if (!taskId) {
      return;
    }

    setIsStopping(true);
    try {
      await stopTask(taskId);
    } finally {
      setIsStopping(false);
    }
  };

  return {
    taskId,
    snapshot,
    events,
    isStarting,
    isResponding,
    isStopping,
    selectedAction,
    startAction,
    respond,
    cancel,
  };
}

function renderPromptTitle(
  prompt: TaskPrompt | null | undefined,
  selectedAction: CalibrationAction | null,
) {
  if (prompt) {
    return prompt.title;
  }

  if (selectedAction === "test") {
    return "校准测试";
  }

  return "当前校准步骤";
}

export function CalibrationPage() {
  const {
    taskId,
    snapshot,
    events,
    isStarting,
    isResponding,
    isStopping,
    selectedAction,
    startAction,
    respond,
    cancel,
  } = useCalibrationTaskWorkflow();

  const calibrationStatusQuery = useQuery({
    queryKey: ["calibration-status", snapshot?.active],
    queryFn: getCalibrationStatus,
  });
  const calibrationStatus = calibrationStatusQuery.data ?? {};

  const prompt = snapshot?.prompt ?? null;
  const summary = summarizeTaskSession(snapshot, {
    isStarting,
    isStopping,
  });
  const [integerValue, setIntegerValue] = useState("5");

  useEffect(() => {
    if (prompt?.kind === "integer") {
      setIntegerValue(String(prompt.default_value ?? 5));
    }
  }, [prompt?.kind, prompt?.step, prompt?.default_value]);

  const [countdown, setCountdown] = useState<number | null>(null);

  // Tick the countdown every second
  useEffect(() => {
    if (countdown === null || countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  // Send record when countdown reaches 0
  useEffect(() => {
    if (countdown === 0) {
      setCountdown(null);
      void respond({ response: "record" });
    }
  }, [countdown, respond]);

  const startRecordCountdown = () => {
    setCountdown(5);
  };

  const parsedIntegerValue =
    prompt?.kind === "integer" && integerValue.trim() !== ""
      ? Number.parseInt(integerValue, 10)
      : Number.NaN;
  const isIntegerPromptValid =
    prompt?.kind !== "integer" ||
    (Number.isInteger(parsedIntegerValue) &&
      parsedIntegerValue >= (prompt.min_value ?? 1));
  const controlsLocked =
    isStarting ||
    isResponding ||
    isStopping ||
    (taskId !== null && (snapshot?.active ?? true));
  const promptButtonsDisabled = isResponding || isStopping;
  const activePromptTitle = renderPromptTitle(prompt, selectedAction);

  return (
    <section aria-label="坐标校准" className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">坐标校准</h1>
          <p className="mt-1 text-sm text-gray-500">
            每次只运行一个校准动作或测试
          </p>
        </div>
        <button
          type="button"
          name="calibration-start-test"
          disabled={controlsLocked || isResponding || isStopping}
          onClick={() => {
            void startAction("test");
          }}
          className="inline-flex h-9 items-center gap-2 rounded-lg bg-gray-900 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-gray-800 active:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Play className="h-3.5 w-3.5" />
          运行测试
        </button>
      </div>

      {/* Calibration Items Grid */}
      <div className="calibration-grid grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {CALIBRATION_ITEMS.map((item) => (
          <article
            key={item.action}
            className="calibration-card rounded-xl border border-gray-200/80 bg-white p-4 shadow-card"
          >
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
              {calibrationStatus[item.action] ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Crosshair className="h-3.5 w-3.5 text-blue-500" />
              )}
              {item.title}
              {calibrationStatus[item.action] ? (
                <span className="ml-auto text-xs font-normal text-green-600">已校准</span>
              ) : (
                <span className="ml-auto text-xs font-normal text-gray-400">未校准</span>
              )}
            </h3>
            <p className="task-status-meta mt-1 text-xs text-gray-500">
              {item.description}
            </p>
            <button
              type="button"
              name={`calibration-start-${item.action}`}
              disabled={controlsLocked || isResponding || isStopping}
              onClick={() => {
                void startAction(item.action);
              }}
              className="mt-3 h-8 w-full rounded-lg border border-gray-200 bg-white text-xs font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 active:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              开始校准
            </button>
          </article>
        ))}
      </div>

      {/* Active Task + Log */}
      <div className="task-grid grid gap-4 lg:grid-cols-2">
        <section className="task-panel rounded-xl border border-gray-200/80 bg-white p-5 shadow-card">
          <div className="task-panel__header">
            <h3 className="text-sm font-semibold text-gray-900">
              {activePromptTitle}
            </h3>
            <p className="mt-0.5 text-xs text-gray-500">{summary.title}</p>
          </div>
          <p className="task-status-meta mt-3 text-sm text-gray-600">
            {prompt?.message ?? summary.description}
          </p>

          {prompt?.kind === "integer" ? (
            <label className="calibration-input mt-3 block">
              <span className="mb-1 block text-xs font-medium text-gray-500">
                输入数值
              </span>
              <input
                type="number"
                min={prompt.min_value ?? 1}
                value={integerValue}
                onChange={(event) => {
                  setIntegerValue(event.target.value);
                }}
                className="h-9 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-800 shadow-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
              />
            </label>
          ) : null}

          <div className="task-actions mt-4 flex flex-wrap gap-2">
            {prompt?.kind === "position" ? (
              <button
                type="button"
                name="calibration-prompt-record"
                disabled={promptButtonsDisabled || countdown !== null}
                onClick={() => {
                  startRecordCountdown();
                }}
                className="h-8 rounded-lg bg-blue-500 px-4 text-xs font-medium text-white shadow-sm transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {countdown !== null
                  ? `${countdown} 秒后记录...`
                  : "记录当前位置"}
              </button>
            ) : null}

            {prompt?.kind === "ack" || prompt?.kind === "integer" ? (
              <button
                type="button"
                name="calibration-prompt-continue"
                disabled={promptButtonsDisabled || !isIntegerPromptValid}
                onClick={() => {
                  const value =
                    prompt.kind === "integer" ? parsedIntegerValue : undefined;
                  void respond({
                    response: "continue",
                    value: Number.isInteger(value) ? value : undefined,
                  });
                }}
                className="h-8 rounded-lg bg-blue-500 px-4 text-xs font-medium text-white shadow-sm transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                继续
              </button>
            ) : null}

            {prompt?.kind === "confirm" ? (
              <>
                <button
                  type="button"
                  name="calibration-prompt-confirm-yes"
                  disabled={promptButtonsDisabled}
                  onClick={() => {
                    void respond({ response: "confirm", accepted: true });
                  }}
                  className="h-8 rounded-lg bg-green-500 px-4 text-xs font-medium text-white shadow-sm transition hover:bg-green-600 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {prompt.confirm_label ?? "是"}
                </button>
                <button
                  type="button"
                  name="calibration-prompt-confirm-no"
                  disabled={promptButtonsDisabled}
                  onClick={() => {
                    void respond({ response: "confirm", accepted: false });
                  }}
                  className="h-8 rounded-lg border border-gray-200 bg-white px-4 text-xs font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {prompt.reject_label ?? "否"}
                </button>
              </>
            ) : null}

            {(prompt || snapshot?.active) && !isStarting ? (
              <button
                type="button"
                name="calibration-prompt-cancel"
                disabled={isStopping}
                onClick={() => {
                  void cancel();
                }}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-red-200 bg-white px-4 text-xs font-medium text-red-600 shadow-sm transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Square className="h-3 w-3" />
                取消
              </button>
            ) : null}
          </div>
        </section>

        <TaskLogPanel
          events={events}
          emptyMessage="开始任一校准项后，步骤日志会显示在这里。"
        />
      </div>
    </section>
  );
}
