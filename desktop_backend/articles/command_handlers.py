from __future__ import annotations

from typing import Any

from services.workflows import (
    reset_empty_content_articles,
    reset_failed_articles,
)
from storage.database import Database
from storage.file_store import FileStore

from .payloads import build_article_payload


def retry_failed_articles_handler(
    *, db: Database | None = None
) -> dict[str, int]:
    db = db or Database()
    return {"affected": reset_failed_articles(db)}


def retry_empty_content_articles_handler(
    *, db: Database | None = None
) -> dict[str, int]:
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


def _load_articles_by_ids(
    db: Database, article_ids: list[int]
) -> list[dict[str, Any]]:
    if not article_ids:
        return []

    rows = db.get_articles_by_ids(article_ids)
    return [build_article_payload(row) for row in rows]
