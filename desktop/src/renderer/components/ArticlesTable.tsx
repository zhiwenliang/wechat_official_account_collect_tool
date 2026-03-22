import type { ArticlePayload } from "../lib/api";

type ArticlesTableProps = {
  articles: ArticlePayload[];
};

export function ArticlesTable({ articles }: ArticlesTableProps) {
  return (
    <div className="articles-table">
      <div className="articles-table__head">
        <span>标题</span>
        <span>状态</span>
        <span>发布时间</span>
      </div>
      {articles.map((article) => (
        <div className="articles-table__row" key={article.id}>
          <div>
            <strong>{article.title || "未命名文章"}</strong>
            <p>{article.url}</p>
          </div>
          <span>{article.status}</span>
          <span>{article.publish_time || "暂无"}</span>
        </div>
      ))}
      {articles.length === 0 ? <p className="articles-table__empty">没有匹配的文章</p> : null}
    </div>
  );
}
