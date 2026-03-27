import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

import { ArticlesTable } from "../../components/ArticlesTable";
import { ArticleDetailModal } from "../../components/ArticleDetailModal";
import { getArticles } from "../../lib/api";
import { useArticlesViewStore } from "../../state/app-store";

function getQueryErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "unknown error";
}

export function ArticlesPage() {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(null);
  const {
    status,
    draftSearch,
    search,
    page,
    pageSize,
    setStatus,
    setDraftSearch,
    submitSearch,
    setPage,
  } = useArticlesViewStore();

  const articlesQuery = useQuery({
    queryKey: ["articles", status, search, page, pageSize],
    queryFn: () =>
      getArticles({
        status,
        search,
        page,
        pageSize,
      }),
  });

  if (articlesQuery.isPending) {
    return (
      <section aria-label="Articles">
        <h1 className="text-xl font-bold text-gray-900">文章管理</h1>
        <p className="mt-2 text-sm text-gray-500">文章列表加载中</p>
        <div className="mt-6 flex justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
        </div>
      </section>
    );
  }

  if (articlesQuery.error) {
    return (
      <section aria-label="Articles">
        <h1 className="text-xl font-bold text-gray-900">文章管理</h1>
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-700">文章列表加载失败</p>
          <p className="mt-1 text-xs text-red-500">
            {getQueryErrorMessage(articlesQuery.error)}
          </p>
        </div>
      </section>
    );
  }

  const payload = articlesQuery.data ?? {
    total: 0,
    page: 1,
    page_size: pageSize,
    items: [],
  };
  const totalPages = Math.max(
    1,
    Math.ceil(payload.total / payload.page_size),
  );
  const isFirstPage = payload.page <= 1;
  const isLastPage = payload.page >= totalPages;

  return (
    <section aria-label="Articles" className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-gray-900">文章管理</h1>
        <p className="mt-1 text-sm text-gray-500">
          共 {payload.total} 篇，当前第 {payload.page} 页
        </p>
      </div>

      {/* Toolbar */}
      <div className="toolbar flex flex-wrap items-end gap-3">
        <label className="toolbar__field">
          <span className="mb-1 block text-xs font-medium text-gray-500">
            状态
          </span>
          <select
            name="article-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="h-9 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-800 shadow-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          >
            <option value="all">全部</option>
            <option value="pending">待抓取</option>
            <option value="scraped">已抓取</option>
            <option value="failed">失败</option>
            <option value="empty">空正文</option>
          </select>
        </label>

        <label className="toolbar__field toolbar__field--grow flex-1">
          <span className="mb-1 block text-xs font-medium text-gray-500">
            搜索
          </span>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <input
              ref={searchInputRef}
              name="article-search"
              defaultValue={draftSearch}
              placeholder="搜索标题或链接"
              onChange={(event) =>
                setDraftSearch((event.target as HTMLInputElement).value)
              }
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  submitSearch(searchInputRef.current?.value);
                }
              }}
              className="h-9 w-full min-w-[180px] rounded-lg border border-gray-200 bg-white pl-8 pr-3 text-sm text-gray-800 shadow-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </label>

        <button
          name="article-search-submit"
          type="button"
          onClick={() => submitSearch(searchInputRef.current?.value)}
          className="h-9 rounded-lg bg-blue-500 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-blue-600 active:bg-blue-700"
        >
          搜索
        </button>
      </div>

      <ArticlesTable
        articles={payload.items}
        onArticleDoubleClick={(article) => setSelectedArticleId(article.id)}
      />

      <ArticleDetailModal
        articleId={selectedArticleId}
        onClose={() => setSelectedArticleId(null)}
      />

      {/* Pagination */}
      <div className="pagination flex items-center justify-end gap-3">
        <button
          name="article-page-prev"
          type="button"
          disabled={isFirstPage}
          onClick={() => setPage(payload.page - 1)}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 text-xs font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          上一页
        </button>
        <span className="text-xs text-gray-500">
          第 {payload.page} / {totalPages} 页
        </span>
        <button
          name="article-page-next"
          type="button"
          disabled={isLastPage}
          onClick={() => setPage(payload.page + 1)}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 text-xs font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          下一页
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </section>
  );
}
