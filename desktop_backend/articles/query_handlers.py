from __future__ import annotations

from storage.database import Database

from .payloads import (
    build_article_detail_payload,
    build_articles_payload,
    build_recent_article_payload,
)

MAX_ARTICLES_PAGE_SIZE = 200


def get_article_detail_handler(*, db: Database, article_id: int):
    row = db.get_article_by_id(article_id)
    if row is None:
        return None
    return build_article_detail_payload(row)


def get_recent_articles_handler(*, db: Database, limit: int = 5):
    safe_limit = max(int(limit), 1)
    rows = db.get_recent_articles(limit=safe_limit)
    return [build_recent_article_payload(row) for row in rows]


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
    safe_page_size = min(max(int(page_size), 1), MAX_ARTICLES_PAGE_SIZE)
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
