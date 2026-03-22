from __future__ import annotations

from typing import Any

from services.workflows import reset_empty_content_articles, reset_failed_articles
from storage.database import Database
from storage.file_store import FileStore

from .schemas import (
    build_article_payload,
    build_articles_payload,
    build_recent_article_payload,
    build_statistics_payload,
)


def get_statistics_handler(*, db: Database):
    return build_statistics_payload(db.get_statistics())


def get_recent_articles_handler(*, db: Database, limit: int = 5):
    safe_limit = max(int(limit), 1)
    return [build_recent_article_payload(row) for row in db.get_recent_articles(limit=safe_limit)]


def get_articles_handler(
    *,
    db: Database,
    status: str = "all",
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    sort_column: str | None = None,
    descending: bool = False,
):
    safe_page = max(int(page), 1)
    safe_page_size = max(int(page_size), 1)
    offset = (safe_page - 1) * safe_page_size
    items = db.get_articles_by_status(
        status=status,
        search=search,
        sort_column=sort_column,
        descending=descending,
        limit=safe_page_size,
        offset=offset,
    )
    total = db.count_articles(status=status, search=search)
    return build_articles_payload(
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        items=items,
    )


def retry_failed_articles_handler(*, db: Database | None = None) -> dict[str, int]:
    db = db or Database()
    return {"affected": reset_failed_articles(db)}


def retry_empty_content_articles_handler(*, db: Database | None = None) -> dict[str, int]:
    db = db or Database()
    return {"affected": reset_empty_content_articles(db)}


def delete_selected_articles_handler(
    *,
    article_ids: list[int],
    db: Database | None = None,
    file_store: FileStore | None = None,
) -> dict[str, Any]:
    db = db or Database()
    file_store = file_store or FileStore()
    normalized_ids = _normalize_article_ids(article_ids)
    selected_articles = _load_articles_by_ids(db, normalized_ids)

    removed_files = 0
    file_errors: list[str] = []
    for article_data in selected_articles:
        try:
            removed_files += len(file_store.delete_article_files(article_data))
        except OSError as exc:
            label = article_data.get("title") or article_data.get("id")
            file_errors.append(f"{label}: {exc}")

    deleted = db.delete_articles_by_ids(normalized_ids)
    return {
        "deleted": deleted,
        "removed_files": removed_files,
        "file_errors": file_errors,
    }


def _normalize_article_ids(article_ids: list[int]) -> list[int]:
    normalized: list[int] = []
    seen: set[int] = set()

    for article_id in article_ids:
        value = int(article_id)
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)

    return normalized


def _load_articles_by_ids(db: Database, article_ids: list[int]) -> list[dict[str, Any]]:
    if not article_ids:
        return []

    selected = set(article_ids)
    return [
        build_article_payload(row)
        for row in db.get_articles_by_status(status="all")
        if row[0] in selected
    ]
