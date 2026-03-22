type TaskProgressPanelProps = {
  status: string;
  current: number;
  total: number;
  message: string;
};

export function TaskProgressPanel({ status, current, total, message }: TaskProgressPanelProps) {
  const safeTotal = Math.max(total, 1);
  const safeCurrent = Math.min(Math.max(current, 0), safeTotal);

  return (
    <section className="task-panel task-progress" aria-label="任务进度">
      <div className="task-panel__header">
        <h3>任务进度</h3>
        <p>{status}</p>
      </div>
      <progress value={safeCurrent} max={safeTotal} />
      <div className="task-progress__meta">
        <span>
          {current} / {total}
        </span>
        <span>{message || "等待进度更新"}</span>
      </div>
    </section>
  );
}
