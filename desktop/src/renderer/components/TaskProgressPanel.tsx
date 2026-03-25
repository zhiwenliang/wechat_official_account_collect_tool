type TaskProgressPanelProps = {
  status: string;
  current: number;
  total: number;
  message: string;
};

export function TaskProgressPanel({
  status,
  current,
  total,
  message,
}: TaskProgressPanelProps) {
  const safeTotal = Math.max(total, 1);
  const safeCurrent = Math.min(Math.max(current, 0), safeTotal);

  return (
    <section
      className="task-panel task-progress rounded-xl border border-gray-200/80 bg-white p-5 shadow-card"
      aria-label="任务进度"
    >
      <div className="task-panel__header flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900">任务进度</h3>
        <p className="text-xs text-gray-500">{status}</p>
      </div>

      <div className="mt-4">
        <progress value={safeCurrent} max={safeTotal} />
      </div>

      <div className="task-progress__meta mt-2 flex flex-wrap justify-between gap-2 text-xs text-gray-500">
        <span>
          {current} / {total}
        </span>
        <span>{message || "等待进度更新"}</span>
      </div>
    </section>
  );
}
