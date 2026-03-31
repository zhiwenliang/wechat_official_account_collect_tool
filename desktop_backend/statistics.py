from __future__ import annotations

from typing import Any, TypedDict

from storage.database import Database

__all__ = [
    "StatisticsPayload",
    "build_statistics_payload",
    "get_statistics_handler",
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


def get_statistics_handler(*, db: Database) -> StatisticsPayload:
    return build_statistics_payload(db.get_statistics())
