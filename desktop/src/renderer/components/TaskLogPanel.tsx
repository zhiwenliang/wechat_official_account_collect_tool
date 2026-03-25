import { cn } from "../lib/utils";
import type { TaskEvent } from "../lib/task-events";
import { formatTaskEventMessage } from "../lib/task-events";

type TaskLogPanelProps = {
  events: TaskEvent[];
  emptyMessage?: string;
};

function eventTypeColor(type: string) {
  switch (type) {
    case "started":
    case "completed":
      return "text-green-600";
    case "error":
      return "text-red-500";
    case "stopped":
    case "cancelled":
      return "text-amber-600";
    case "progress":
      return "text-blue-500";
    case "prompt":
      return "text-purple-500";
    default:
      return "text-gray-500";
  }
}

export function TaskLogPanel({
  events,
  emptyMessage = "开始任务后，日志会按时间顺序追加显示。",
}: TaskLogPanelProps) {
  return (
    <section
      className="task-panel task-log rounded-xl border border-gray-200/80 bg-white p-5 shadow-card"
      aria-label="任务日志"
    >
      <div className="task-panel__header flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900">任务日志</h3>
        <p className="text-xs text-gray-500">追加式事件流</p>
      </div>

      {events.length > 0 ? (
        <ol className="task-log__list mt-3 max-h-96 space-y-1.5 overflow-y-auto">
          {events.map((event, index) => (
            <li
              className={cn(
                "task-log__item rounded-lg bg-gray-50 px-3 py-2",
                `task-log__item--${event.type}`,
              )}
              key={`${event.task_id}-${event.type}-${index}`}
            >
              <strong
                className={cn(
                  "block text-[11px] font-semibold uppercase tracking-wider",
                  eventTypeColor(event.type),
                )}
              >
                {event.type}
              </strong>
              <p className="mt-0.5 whitespace-pre-wrap break-words text-xs text-gray-700">
                {formatTaskEventMessage(event)}
              </p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="task-log__empty mt-3 text-xs text-gray-400">
          {emptyMessage}
        </p>
      )}
    </section>
  );
}
