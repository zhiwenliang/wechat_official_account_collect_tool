import type { ArticlePayload } from "../lib/api";
import { cn } from "../lib/utils";

type ArticlesTableProps = {
  articles: ArticlePayload[];
};

function statusBadge(status: string) {
  switch (status) {
    case "scraped":
      return "bg-green-50 text-green-700 border-green-200";
    case "failed":
      return "bg-red-50 text-red-700 border-red-200";
    case "pending":
      return "bg-amber-50 text-amber-700 border-amber-200";
    default:
      return "bg-gray-50 text-gray-600 border-gray-200";
  }
}

export function ArticlesTable({ articles }: ArticlesTableProps) {
  return (
    <div className="articles-table overflow-hidden rounded-xl border border-gray-200/80 bg-white shadow-card">
      {/* Header */}
      <div className="articles-table__head grid grid-cols-[minmax(280px,2fr)_100px_160px] gap-4 border-b border-gray-100 px-5 py-2.5 text-xs font-medium uppercase tracking-wide text-gray-500 max-sm:hidden">
        <span>标题</span>
        <span>状态</span>
        <span>发布时间</span>
      </div>

      {/* Rows */}
      {articles.map((article) => (
        <div
          className="articles-table__row grid grid-cols-[minmax(280px,2fr)_100px_160px] items-center gap-4 border-b border-gray-50 px-5 py-3 transition-colors last:border-b-0 hover:bg-gray-50/60 max-sm:grid-cols-1"
          key={article.id}
        >
          <div className="min-w-0">
            <strong className="block truncate text-sm font-medium text-gray-900">
              {article.title || "未命名文章"}
            </strong>
            <p className="mt-0.5 truncate text-xs text-gray-400">
              {article.url}
            </p>
          </div>
          <span>
            <span
              className={cn(
                "inline-block rounded-md border px-2 py-0.5 text-xs font-medium",
                statusBadge(article.status),
              )}
            >
              {article.status}
            </span>
          </span>
          <span className="text-sm text-gray-500">
            {article.publish_time || "暂无"}
          </span>
        </div>
      ))}

      {articles.length === 0 ? (
        <p className="articles-table__empty px-5 py-8 text-center text-sm text-gray-400">
          没有匹配的文章
        </p>
      ) : null}
    </div>
  );
}
