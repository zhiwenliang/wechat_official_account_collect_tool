import { useQuery } from "@tanstack/react-query";

import { getRecentArticles, getStatistics } from "../../lib/api";
import { StatisticsCards } from "../../components/StatisticsCards";

function getQueryErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "unknown error";
}

export function DashboardPage() {
  const statisticsQuery = useQuery({
    queryKey: ["statistics"],
    queryFn: getStatistics,
  });
  const recentArticlesQuery = useQuery({
    queryKey: ["recent-articles"],
    queryFn: () => getRecentArticles(5),
  });
  const dashboardError = statisticsQuery.error ?? recentArticlesQuery.error;

  if (statisticsQuery.isPending || recentArticlesQuery.isPending) {
    return (
      <section className="shell__hero" aria-label="Dashboard">
        <p className="shell__eyebrow">Dashboard</p>
        <h2>概览</h2>
        <p className="shell__description">概览数据加载中</p>
      </section>
    );
  }

  if (dashboardError) {
    return (
      <section className="shell__hero" aria-label="Dashboard">
        <p className="shell__eyebrow">Dashboard</p>
        <h2>概览</h2>
        <p className="shell__description">概览数据加载失败</p>
        <p className="shell__description">{getQueryErrorMessage(dashboardError)}</p>
      </section>
    );
  }

  const stats = statisticsQuery.data ?? {
    total: 0,
    pending: 0,
    scraped: 0,
    failed: 0,
    empty_content: 0,
    failed_urls: [],
  };
  const recentArticles = [...(recentArticlesQuery.data ?? [])].sort((left, right) =>
    right.publish_time.localeCompare(left.publish_time),
  );

  return (
    <section className="shell__hero" aria-label="Dashboard">
      <p className="shell__eyebrow">Dashboard</p>
      <h2>概览</h2>
      <StatisticsCards stats={stats} />

      <div className="panel-list">
        <section>
          <h3>最近文章</h3>
          <div className="recent-list">
            {recentArticles.map((article) => (
              <article key={article.id} className="recent-list__item">
                <strong>{article.title || "未命名文章"}</strong>
                <span>{article.publish_time || "暂无发布时间"}</span>
                <span>{article.status}</span>
              </article>
            ))}
            {recentArticles.length === 0 ? <p>暂无最近文章</p> : null}
          </div>
        </section>

        <section>
          <h3>下一步建议</h3>
          <ul className="guidance-list">
            <li>先检查待抓取和失败数，再决定是否启动新任务。</li>
            <li>文章管理页支持按状态筛选和关键词搜索。</li>
          </ul>
        </section>
      </div>
    </section>
  );
}
