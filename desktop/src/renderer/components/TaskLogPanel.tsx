import type { TaskEvent } from "../lib/task-events";
import { formatTaskEventMessage } from "../lib/task-events";

type TaskLogPanelProps = {
  events: TaskEvent[];
  emptyMessage?: string;
};

export function TaskLogPanel({ events, emptyMessage = "开始任务后，日志会按时间顺序追加显示。" }: TaskLogPanelProps) {
  return (
    <section className="task-panel task-log" aria-label="任务日志">
      <div className="task-panel__header">
        <h3>任务日志</h3>
        <p>追加式事件流</p>
      </div>
      {events.length > 0 ? (
        <ol className="task-log__list">
          {events.map((event, index) => (
            <li className={`task-log__item task-log__item--${event.type}`} key={`${event.task_id}-${event.type}-${index}`}>
              <strong>{event.type}</strong>
              <p>{formatTaskEventMessage(event)}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="task-log__empty">{emptyMessage}</p>
      )}
    </section>
  );
}
