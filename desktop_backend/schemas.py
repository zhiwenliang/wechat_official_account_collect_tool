from typing import Any, TypedDict

from .articles.payloads import (
    ArticleDetailPayload,
    ArticlePayload,
    ArticlesPayload,
    RecentArticlePayload,
    build_article_detail_payload,
    build_article_payload,
    build_articles_payload,
    build_recent_article_payload,
)

__all__ = [
    "ArticleDetailPayload",
    "ArticlePayload",
    "ArticlesPayload",
    "RecentArticlePayload",
    "StatisticsPayload",
    "build_article_detail_payload",
    "build_article_payload",
    "build_articles_payload",
    "build_recent_article_payload",
    "build_statistics_payload",
]


class StatisticsPayload(TypedDict):
    total: int
    pending: int
    scraped: int
    failed: int
    empty_content: int
    failed_urls: list[str]


def build_statistics_payload(stats: dict[str, Any]) -> StatisticsPayload:
    return {
        "total": int(stats.get("total", 0)),
        "pending": int(stats.get("pending", 0)),
        "scraped": int(stats.get("scraped", 0)),
        "failed": int(stats.get("failed", 0)),
        "empty_content": int(stats.get("empty_content", 0)),
        "failed_urls": list(stats.get("failed_urls", [])),
    }
