from __future__ import annotations

from typing import Callable

from .calibration.runtime import default_calibration_runtime_factory

CollectorFactory = Callable[[], object]
ScraperFactory = Callable[[], object]
DatabaseFactory = Callable[[], object]
FileStoreFactory = Callable[[], object]
PendingArticlesProvider = Callable[[], object]
CalibrationRuntimeFactory = Callable[[], object]


def default_collector_factory():
    from scraper.link_collector import LinkCollector

    return LinkCollector()


def default_scraper_factory():
    from scraper.content_scraper import ContentScraper

    return ContentScraper()


def default_db_factory():
    from storage.database import Database

    return Database()


def default_file_store_factory():
    from storage.file_store import FileStore

    return FileStore()

