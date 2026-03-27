from __future__ import annotations

import time
from typing import Callable

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


class DesktopCalibrationRuntime:
    def __init__(self) -> None:
        import pyautogui

        self._pyautogui = pyautogui

    def get_current_position(self):
        return self._pyautogui.position()

    def click(self, x: int, y: int) -> None:
        self._pyautogui.click(x, y)

    def scroll(self, amount: int) -> None:
        self._pyautogui.scroll(amount)

    def move_to(self, x: int, y: int, duration: float) -> None:
        self._pyautogui.moveTo(x, y, duration)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def default_calibration_runtime_factory():
    return DesktopCalibrationRuntime()
