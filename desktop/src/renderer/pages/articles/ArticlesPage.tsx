import { useQuery } from "@tanstack/react-query";

import { ArticlesTable } from "../../components/ArticlesTable";
import { getArticles } from "../../lib/api";
import { useArticlesViewStore } from "../../state/app-store";

export function ArticlesPage() {
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

  const payload = articlesQuery.data ?? {
    total: 0,
    page: 1,
    page_size: pageSize,
    items: [],
  };
  const totalPages = Math.max(1, Math.ceil(payload.total / payload.page_size));
  const isFirstPage = payload.page <= 1;
  const isLastPage = payload.page >= totalPages;

  return (
    <section className="shell__hero" aria-label="Articles">
      <p className="shell__eyebrow">Articles</p>
      <h2>文章管理</h2>

      <div className="toolbar">
        <label className="toolbar__field">
          <span>状态</span>
          <select
            name="article-status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">全部</option>
            <option value="pending">待抓取</option>
            <option value="scraped">已抓取</option>
            <option value="failed">失败</option>
            <option value="empty">空正文</option>
          </select>
        </label>

        <label className="toolbar__field toolbar__field--grow">
          <span>搜索</span>
          <input
            name="article-search"
            value={draftSearch}
            placeholder="搜索标题或链接"
            onInput={(event) => setDraftSearch((event.target as HTMLInputElement).value)}
          />
        </label>

        <button name="article-search-submit" type="button" onClick={() => submitSearch()}>
          搜索
        </button>
      </div>

      <p className="shell__description">共 {payload.total} 篇，当前第 {payload.page} 页</p>
      <ArticlesTable articles={payload.items} />
      <div className="pagination">
        <button
          name="article-page-prev"
          type="button"
          disabled={isFirstPage}
          onClick={() => setPage(payload.page - 1)}
        >
          上一页
        </button>
        <span>
          第 {payload.page} / {totalPages} 页
        </span>
        <button
          name="article-page-next"
          type="button"
          disabled={isLastPage}
          onClick={() => setPage(payload.page + 1)}
        >
          下一页
        </button>
      </div>
    </section>
  );
}
