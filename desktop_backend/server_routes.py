from __future__ import annotations

from typing import Any

from storage.database import Database


def build_article_detail_response(
    db: Database, *, article_id: int
) -> tuple[int, Any]:
    from desktop_backend.articles.query_handlers import get_article_detail_handler
    payload = get_article_detail_handler(db=db, article_id=article_id)
    if payload is None:
        return 404, {"status": "error", "message": "article not found"}
    return 200, payload


def _statistics_route(server: Any):
    def handler(_query: Any) -> Any:
        from desktop_backend.statistics import get_statistics_handler
        return get_statistics_handler(db=server.db)
    return handler


def _recent_articles_route(server: Any):
    def handler(query: Any) -> Any:
        from desktop_backend.articles.query_handlers import get_recent_articles_handler
        from desktop_backend.http.parsing import parse_int
        return get_recent_articles_handler(
            db=server.db,
            limit=parse_int(query, "limit", 5),
        )
    return handler


def _articles_route(server: Any):
    def handler(query: Any) -> Any:
        from desktop_backend.articles.query_handlers import get_articles_handler
        from desktop_backend.http.parsing import parse_bool, parse_int
        return get_articles_handler(
            db=server.db,
            status=query.get("status", ["all"])[0],
            search=query.get("search", [""])[0],
            page=parse_int(query, "page", 1),
            page_size=parse_int(query, "page_size", 20),
            sort_column=query.get("sort_column", [None])[0],
            descending=parse_bool(query, "descending"),
        )
    return handler


def _calibration_status_route():
    def handler(_query: Any) -> Any:
        from desktop_backend.tasks.calibration.status import get_calibration_status_handler
        return get_calibration_status_handler()
    return handler


def _article_detail_route(server: Any):
    def handler(query: Any) -> Any:
        from desktop_backend.http.parsing import parse_int
        return build_article_detail_response(
            server.db, article_id=parse_int(query, "id", 0)
        )
    return handler


def register_query_routes(server: Any) -> None:
    server._routes[("GET", "/api/statistics")] = _statistics_route(server)
    server._routes[("GET", "/api/recent-articles")] = _recent_articles_route(server)
    server._routes[("GET", "/api/articles")] = _articles_route(server)
    server._routes[("GET", "/api/calibration/status")] = _calibration_status_route()
    server._routes[("GET", "/api/article-detail")] = _article_detail_route(server)
