import type { StatisticsPayload } from "../lib/api";

type StatisticsCardsProps = {
  stats: StatisticsPayload;
};

const cardItems = [
  { key: "total", label: "文章总数" },
  { key: "pending", label: "待抓取" },
  { key: "scraped", label: "已抓取" },
  { key: "failed", label: "失败" },
  { key: "empty_content", label: "空正文" },
] as const;

export function StatisticsCards({ stats }: StatisticsCardsProps) {
  return (
    <div className="stats-grid">
      {cardItems.map((item) => (
        <article className="stat-card" key={item.key}>
          <p className="stat-card__label">{item.label}</p>
          <strong className="stat-card__value">{stats[item.key]}</strong>
        </article>
      ))}
    </div>
  );
}
