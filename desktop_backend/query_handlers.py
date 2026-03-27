from __future__ import annotations

from storage.database import Database

from .articles.command_handlers import (
    delete_selected_articles_handler,
    retry_empty_content_articles_handler,
    retry_failed_articles_handler,
)
from .articles.query_handlers import (
    MAX_ARTICLES_PAGE_SIZE,
    get_article_detail_handler,
    get_articles_handler,
    get_recent_articles_handler,
)
from .schemas import build_statistics_payload
from .tasks.calibration.status import get_calibration_status_handler

__all__ = [
    "MAX_ARTICLES_PAGE_SIZE",
    "delete_selected_articles_handler",
    "get_article_detail_handler",
    "get_articles_handler",
    "get_calibration_status_handler",
    "get_recent_articles_handler",
    "get_statistics_handler",
    "retry_empty_content_articles_handler",
    "retry_failed_articles_handler",
]


def get_statistics_handler(*, db: Database):
    return build_statistics_payload(db.get_statistics())
