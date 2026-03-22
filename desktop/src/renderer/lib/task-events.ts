export type BackendHealth = {
  status: "ok";
  service: string;
};

export type BackendStatus =
  | {
      state: "starting";
      message: string;
    }
  | {
      state: "ready";
      baseUrl: string;
      health: BackendHealth;
    }
  | {
      state: "error";
      message: string;
    };

export type TaskType = "collection" | "scrape";

export type TaskStartedEvent = {
  type: "started";
  task_id: string;
  task_type: TaskType;
};

export type TaskLogEvent = {
  type: "log";
  task_id: string;
  message: string;
};

export type TaskProgressEvent = {
  type: "progress";
  task_id: string;
  current: number;
  total: number;
  message: string;
  success?: number;
  failed?: number;
};

export type TaskStatusEvent = {
  type: "status";
  task_id: string;
  status: string;
  message: string;
};

export type TaskCompletedEvent = {
  type: "completed";
  task_id: string;
  task_type: TaskType;
};

export type TaskErrorEvent = {
  type: "error";
  task_id: string;
  message: string;
};

export type TaskStoppedEvent = {
  type: "stopped";
  task_id: string;
  reason: string;
};

export type TaskCancelledEvent = {
  type: "cancelled";
  task_id: string;
  reason: string;
};

export type TaskEvent =
  | TaskStartedEvent
  | TaskLogEvent
  | TaskProgressEvent
  | TaskStatusEvent
  | TaskCompletedEvent
  | TaskErrorEvent
  | TaskStoppedEvent
  | TaskCancelledEvent;

export type TaskSnapshotPayload = {
  task_id: string;
  task_type: TaskType;
  active: boolean;
  stopping: boolean;
  events: TaskEvent[];
};

export type TaskProgressSummary = {
  current: number;
  total: number;
  message: string;
  percent: number;
  hasProgress: boolean;
  success: number | null;
  failed: number | null;
};

export type TaskSessionSummary = {
  title: string;
  description: string;
};

export function getTaskDisplayName(taskType: TaskType) {
  return taskType === "collection" ? "采集" : "抓取";
}

export function isTerminalTaskEvent(event: TaskEvent) {
  return event.type === "completed" || event.type === "error" || event.type === "stopped" || event.type === "cancelled";
}

export function formatTaskEventMessage(event: TaskEvent) {
  switch (event.type) {
    case "started":
      return `${getTaskDisplayName(event.task_type)}任务已开始`;
    case "log":
      return event.message;
    case "progress":
      return event.message || `已处理 ${event.current}/${event.total}`;
    case "status":
      return event.message || event.status;
    case "completed":
      return `${getTaskDisplayName(event.task_type)}任务已完成`;
    case "error":
      return event.message || "任务失败";
    case "stopped":
      return event.reason || "任务已停止";
    case "cancelled":
      return event.reason || "任务已取消";
  }
}

export function summarizeTaskProgress(events: TaskEvent[]): TaskProgressSummary {
  const lastProgressEvent = [...events].reverse().find((event): event is TaskProgressEvent => event.type === "progress");

  if (!lastProgressEvent) {
    return {
      current: 0,
      total: 0,
      message: "",
      percent: 0,
      hasProgress: false,
      success: null,
      failed: null,
    };
  }

  const safeTotal = Math.max(lastProgressEvent.total, 0);
  const safeCurrent = Math.max(lastProgressEvent.current, 0);
  const percent = safeTotal > 0 ? Math.min(Math.round((safeCurrent / safeTotal) * 100), 100) : 0;

  return {
    current: safeCurrent,
    total: safeTotal,
    message: lastProgressEvent.message,
    percent,
    hasProgress: true,
    success: typeof lastProgressEvent.success === "number" ? lastProgressEvent.success : null,
    failed: typeof lastProgressEvent.failed === "number" ? lastProgressEvent.failed : null,
  };
}

function taskEventsMatch(left: TaskEvent, right: TaskEvent) {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function mergeTaskEvents(existing: TaskEvent[], snapshotEvents: TaskEvent[]) {
  if (existing.length === 0) {
    return [...snapshotEvents];
  }

  if (snapshotEvents.length < existing.length) {
    return [...snapshotEvents];
  }

  const matchesPrefix = existing.every((event, index) => taskEventsMatch(event, snapshotEvents[index]));
  if (!matchesPrefix) {
    return [...snapshotEvents];
  }

  return existing.concat(snapshotEvents.slice(existing.length));
}

export function summarizeTaskSession(
  snapshot: TaskSnapshotPayload | null,
  options?: {
    isStarting?: boolean;
    isStopping?: boolean;
  },
): TaskSessionSummary {
  if (options?.isStarting) {
    return {
      title: "启动中",
      description: "正在创建任务，请稍候。",
    };
  }

  if (!snapshot) {
    return {
      title: "未开始",
      description: "点击开始按钮后，任务日志和进度会在这里更新。",
    };
  }

  const lastTerminalEvent = [...snapshot.events].reverse().find((event) => isTerminalTaskEvent(event));
  if (lastTerminalEvent?.type === "completed") {
    return {
      title: "已完成",
      description: "任务已经完成，可以重新开始新的任务。",
    };
  }

  if (lastTerminalEvent?.type === "error") {
    return {
      title: "失败",
      description: lastTerminalEvent.message || "任务执行失败。",
    };
  }

  if (lastTerminalEvent?.type === "stopped" || lastTerminalEvent?.type === "cancelled") {
    return {
      title: "已停止",
      description: lastTerminalEvent.reason || "任务已停止。",
    };
  }

  if (options?.isStopping || snapshot?.stopping) {
    return {
      title: "停止中",
      description: "停止请求已发送，正在等待任务结束。",
    };
  }

  return {
    title: snapshot.active ? "进行中" : "已结束",
    description: snapshot.active
      ? "任务正在运行，页面会自动轮询最新事件。"
      : "任务已经结束，当前显示的是最后一次快照。",
  };
}
