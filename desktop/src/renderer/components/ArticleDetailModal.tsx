import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { getArticleDetail, getBackendStatus } from "../lib/api";
import { cn } from "../lib/utils";

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

type ArticleDetailModalProps = {
  articleId: number | null;
  onClose: () => void;
};

export function ArticleDetailModal({
  articleId,
  onClose,
}: ArticleDetailModalProps) {
  const detailQuery = useQuery({
    queryKey: ["article-detail", articleId],
    queryFn: () => getArticleDetail(articleId!),
    enabled: articleId !== null,
  });

  const [proxyBase, setProxyBase] = useState<string | null>(null);

  useEffect(() => {
    getBackendStatus().then((s) => {
      if (s.state === "ready") setProxyBase(s.baseUrl);
    });
  }, []);

  useEffect(() => {
    if (articleId === null) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [articleId, onClose]);

  if (articleId === null) return null;

  const article = detailQuery.data;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative mx-4 flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-start gap-3 border-b border-gray-100 px-6 py-4">
          <div className="min-w-0 flex-1">
            {detailQuery.isPending ? (
              <div className="h-5 w-48 animate-pulse rounded bg-gray-200" />
            ) : (
              <>
                <h2 className="text-base font-semibold text-gray-900">
                  {article?.title || "未命名文章"}
                </h2>
                <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                  {article && (
                    <span
                      className={cn(
                        "inline-block rounded-md border px-2 py-0.5 text-xs font-medium",
                        statusBadge(article.status),
                      )}
                    >
                      {article.status}
                    </span>
                  )}
                  {article?.publish_time && (
                    <span>发布于 {article.publish_time}</span>
                  )}
                  {article?.scraped_at && (
                    <span>抓取于 {article.scraped_at}</span>
                  )}
                </div>
                {article?.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 block truncate text-xs text-blue-500 hover:underline"
                  >
                    {article.url}
                  </a>
                )}
              </>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {detailQuery.isPending ? (
            <div className="space-y-2">
              <div className="h-4 w-full animate-pulse rounded bg-gray-100" />
              <div className="h-4 w-3/4 animate-pulse rounded bg-gray-100" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-gray-100" />
            </div>
          ) : detailQuery.error ? (
            <p className="text-sm text-red-500">加载失败</p>
          ) : article?.content_markdown ? (
            <div className="prose prose-sm max-w-none text-gray-700">
              <Markdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => {
                    const proxied =
                      src && proxyBase
                        ? `${proxyBase}/api/image-proxy?url=${encodeURIComponent(src)}`
                        : src;
                    return (
                      <img
                        src={proxied}
                        alt={alt || ""}
                        className="max-w-full rounded"
                        loading="lazy"
                      />
                    );
                  },
                }}
              >
                {article.content_markdown}
              </Markdown>
            </div>
          ) : (
            <p className="text-sm text-gray-400">暂无正文内容</p>
          )}
        </div>
      </div>
    </div>
  );
}
