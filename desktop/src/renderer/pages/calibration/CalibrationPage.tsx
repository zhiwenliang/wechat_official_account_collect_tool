import { useEffect, useState } from "react";

import { TaskLogPanel } from "../../components/TaskLogPanel";
import {
  getTaskSnapshot,
  respondToCalibrationTask,
  startCalibrationTask,
  stopTask,
  type CalibrationAction,
} from "../../lib/api";
import type { TaskEvent, TaskPrompt, TaskSnapshotPayload } from "../../lib/task-events";
import { mergeTaskEvents, summarizeTaskSession } from "../../lib/task-events";

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
  const [selectedAction, setSelectedAction] = useState<CalibrationAction | null>(null);

  useEffect(() => {
    if (!taskId) {
      return;
    }

    let cancelled = false;

    const syncTaskSnapshot = async () => {
      try {
        const nextSnapshot = await getTaskSnapshot(taskId);
        if (cancelled) {
          return;
        }

        setSnapshot(nextSnapshot);
        setEvents((current) => mergeTaskEvents(current, nextSnapshot.events));

        if (!nextSnapshot.active) {
          setIsStopping(false);
          setIsResponding(false);
        }
      } catch (_error: unknown) {
        if (!cancelled) {
          setIsStopping(false);
          setIsResponding(false);
        }
      }
    };

    void syncTaskSnapshot();
    const intervalId = window.setInterval(() => {
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

function renderPromptTitle(prompt: TaskPrompt | null | undefined, selectedAction: CalibrationAction | null) {
  if (prompt) {
    return prompt.title;
  }

  if (selectedAction === "test") {
    return "校准测试";
  }

  return "当前校准步骤";
}

export function CalibrationPage() {
  const { taskId, snapshot, events, isStarting, isResponding, isStopping, selectedAction, startAction, respond, cancel } =
    useCalibrationTaskWorkflow();
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

  const parsedIntegerValue =
    prompt?.kind === "integer" && integerValue.trim() !== "" ? Number.parseInt(integerValue, 10) : Number.NaN;
  const isIntegerPromptValid =
    prompt?.kind !== "integer" ||
    (Number.isInteger(parsedIntegerValue) && parsedIntegerValue >= (prompt.min_value ?? 1));
  const controlsLocked = isStarting || isResponding || isStopping || (taskId !== null && (snapshot?.active ?? true));
  const promptButtonsDisabled = isResponding || isStopping;
  const activePromptTitle = renderPromptTitle(prompt, selectedAction);

  return (
    <section className="shell__hero task-page" aria-label="坐标校准">
      <div className="task-panel__header">
        <div>
          <p className="shell__eyebrow">Calibration</p>
          <h2>坐标校准</h2>
          <p className="shell__description">保持 Tkinter 的按项校准模型，每次只运行一个校准动作或测试。</p>
        </div>
        <button
          type="button"
          name="calibration-start-test"
          disabled={controlsLocked || isResponding || isStopping}
          onClick={() => {
            void startAction("test");
          }}
        >
          运行测试
        </button>
      </div>

      <div className="calibration-grid">
        {CALIBRATION_ITEMS.map((item) => (
          <article key={item.action} className="task-panel calibration-card">
            <h3>{item.title}</h3>
            <p className="task-status-meta">{item.description}</p>
            <button
              type="button"
              name={`calibration-start-${item.action}`}
              disabled={controlsLocked || isResponding || isStopping}
              onClick={() => {
                void startAction(item.action);
              }}
            >
              开始校准
            </button>
          </article>
        ))}
      </div>

      <div className="task-grid">
        <section className="task-panel">
          <div className="task-panel__header">
            <div>
              <h3>{activePromptTitle}</h3>
              <p>{summary.title}</p>
            </div>
          </div>
          <p className="task-status-meta">{prompt?.message ?? summary.description}</p>
          {prompt?.kind === "integer" ? (
            <label className="calibration-input">
              <span>输入数值</span>
              <input
                type="number"
                min={prompt.min_value ?? 1}
                value={integerValue}
                onChange={(event) => {
                  setIntegerValue(event.target.value);
                }}
              />
            </label>
          ) : null}
          <div className="task-actions">
            {prompt?.kind === "position" ? (
              <button
                type="button"
                name="calibration-prompt-record"
                disabled={promptButtonsDisabled}
                onClick={() => {
                  void respond({ response: "record" });
                }}
              >
                记录当前位置
              </button>
            ) : null}

            {prompt?.kind === "ack" || prompt?.kind === "integer" ? (
              <button
                type="button"
                name="calibration-prompt-continue"
                disabled={promptButtonsDisabled || !isIntegerPromptValid}
                onClick={() => {
                  const value = prompt.kind === "integer" ? parsedIntegerValue : undefined;
                  void respond({ response: "continue", value: Number.isInteger(value) ? value : undefined });
                }}
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
              >
                取消
              </button>
            ) : null}
          </div>
        </section>

        <TaskLogPanel events={events} emptyMessage="开始任一校准项后，步骤日志会显示在这里。" />
      </div>
    </section>
  );
}
