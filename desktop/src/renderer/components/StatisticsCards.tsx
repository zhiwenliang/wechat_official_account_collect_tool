import { cn } from "../lib/utils";
import type { StatisticsPayload } from "../lib/api";

type StatisticsCardsProps = {
  stats: StatisticsPayload;
};

const cardItems = [
  { key: "total", label: "文章总数", color: "text-gray-900" },
  { key: "pending", label: "待抓取", color: "text-amber-600" },
  { key: "scraped", label: "已抓取", color: "text-green-600" },
  { key: "failed", label: "失败", color: "text-red-500" },
  { key: "empty_content", label: "空正文", color: "text-gray-400" },
] as const;

export function StatisticsCards({ stats }: StatisticsCardsProps) {
  return (
    <div className="stats-grid grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {cardItems.map((item) => (
        <article
          className="stat-card rounded-xl border border-gray-200/80 bg-white p-4 shadow-card transition-shadow hover:shadow-card-hover"
          key={item.key}
        >
          <p className="stat-card__label text-xs font-medium uppercase tracking-wide text-gray-500">
            {item.label}
          </p>
          <strong
            className={cn(
              "stat-card__value mt-2 block text-2xl font-semibold",
              item.color,
            )}
          >
            {stats[item.key]}
          </strong>
        </article>
      ))}
    </div>
  );
}
