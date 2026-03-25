import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Lightbulb } from "lucide-react";

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
      <section aria-label="Dashboard">
        <h1 className="text-xl font-bold text-gray-900">概览</h1>
        <p className="mt-2 text-sm text-gray-500">概览数据加载中</p>
        <div className="mt-6 flex justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
        </div>
      </section>
    );
  }

  if (dashboardError) {
    return (
      <section aria-label="Dashboard">
        <h1 className="text-xl font-bold text-gray-900">概览</h1>
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-700">概览数据加载失败</p>
          <p className="mt-1 text-xs text-red-500">
            {getQueryErrorMessage(dashboardError)}
          </p>
        </div>
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
  const recentArticles = [...(recentArticlesQuery.data ?? [])].sort(
    (left, right) => right.publish_time.localeCompare(left.publish_time),
  );

  return (
    <section aria-label="Dashboard" className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">概览</h1>
        <p className="mt-1 text-sm text-gray-500">
          查看采集和抓取的整体状态
        </p>
      </div>

      <StatisticsCards stats={stats} />

      <div className="grid gap-4 md:grid-cols-2">
        {/* Recent Articles */}
        <div className="rounded-xl border border-gray-200/80 bg-white p-5 shadow-card">
          <h3 className="text-sm font-semibold text-gray-900">最近文章</h3>
          <div className="recent-list mt-3 space-y-2">
            {recentArticles.map((article) => (
              <article
                key={article.id}
                className="recent-list__item flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <strong className="block truncate text-sm font-medium text-gray-800">
                    {article.title || "未命名文章"}
                  </strong>
                  <span className="text-xs text-gray-400">
                    {article.publish_time || "暂无发布时间"}
                  </span>
                </div>
                <span className="ml-3 shrink-0 text-xs text-gray-400">
                  {article.status}
                </span>
              </article>
            ))}
            {recentArticles.length === 0 ? (
              <p className="py-4 text-center text-xs text-gray-400">
                暂无最近文章
              </p>
            ) : null}
          </div>
        </div>

        {/* Next Steps */}
        <div className="rounded-xl border border-gray-200/80 bg-white p-5 shadow-card">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            下一步建议
          </h3>
          <ul className="guidance-list mt-3 space-y-2">
            <li className="flex items-start gap-2 text-sm text-gray-600">
              <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
              先检查待抓取和失败数，再决定是否启动新任务。
            </li>
            <li className="flex items-start gap-2 text-sm text-gray-600">
              <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gray-400" />
              文章管理页支持按状态筛选和关键词搜索。
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
