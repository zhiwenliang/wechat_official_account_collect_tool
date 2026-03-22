from storage.database import Database

from .schemas import (
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
