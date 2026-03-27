from __future__ import annotations

from typing import Any

from desktop_backend.articles.query_handlers import (
    get_article_detail_handler,
    get_articles_handler,
    get_recent_articles_handler,
)
from desktop_backend.http.parsing import parse_bool, parse_int
from desktop_backend.query_handlers import get_statistics_handler
from desktop_backend.tasks.calibration.status import get_calibration_status_handler
from storage.database import Database


def build_article_detail_response(
    db: Database, *, article_id: int
) -> tuple[int, Any]:
    payload = get_article_detail_handler(db=db, article_id=article_id)
    if payload is None:
        return 404, {"status": "error", "message": "article not found"}
    return 200, payload


def register_query_routes(server: Any) -> None:
    server._routes[("GET", "/api/statistics")] = (
        lambda _query: get_statistics_handler(db=server.db)
    )
    server._routes[("GET", "/api/recent-articles")] = (
        lambda query: get_recent_articles_handler(
            db=server.db,
            limit=parse_int(query, "limit", 5),
        )
    )
    server._routes[("GET", "/api/articles")] = lambda query: get_articles_handler(
        db=server.db,
        status=query.get("status", ["all"])[0],
        search=query.get("search", [""])[0],
        page=parse_int(query, "page", 1),
        page_size=parse_int(query, "page_size", 20),
        sort_column=query.get("sort_column", [None])[0],
        descending=parse_bool(query, "descending"),
    )
    server._routes[("GET", "/api/calibration/status")] = (
        lambda _query: get_calibration_status_handler()
    )
    server._routes[("GET", "/api/article-detail")] = (
        lambda query: build_article_detail_response(
            server.db, article_id=parse_int(query, "id", 0)
        )
    )
