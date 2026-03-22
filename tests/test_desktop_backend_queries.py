import shutil
import sqlite3
import unittest
import uuid
from pathlib import Path

from desktop_backend.query_handlers import (
    get_articles_handler,
    get_recent_articles_handler,
    get_statistics_handler,
)
from storage.database import Database


TEST_TMP_ROOT = Path("tmp_test_workspace")


def make_case_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def make_database(root: Path) -> Database:
    return Database(root / "articles.db")


def seed_article(
    db: Database,
    *,
    url: str,
    title: str = "",
    status: str = "pending",
    publish_time: str = "",
    scraped_at: str = "",
    file_path: str = "",
    content_html: str = "",
    content_markdown: str = "",
) -> None:
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO articles (
            title, url, publish_time, scraped_at, status,
            file_path, content_html, content_markdown
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            url,
            publish_time,
            scraped_at,
            status,
            file_path,
            content_html,
            content_markdown,
        ),
    )
    conn.commit()
    conn.close()


class DesktopBackendQueryTests(unittest.TestCase):
    def test_get_statistics_returns_expected_counts(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db = make_database(root)
        seed_article(db, url="https://example.com/1")

        result = get_statistics_handler(db=db)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["pending"], 1)
        self.assertEqual(result["scraped"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["empty_content"], 0)
        self.assertEqual(result["failed_urls"], [])

    def test_get_recent_articles_returns_newest_articles_first(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db = make_database(root)
        seed_article(db, url="https://example.com/old", title="Old", publish_time="2024-01-01 08:00:00")
        seed_article(db, url="https://example.com/new", title="New", publish_time="2024-01-02 08:00:00")
        seed_article(db, url="https://example.com/untimed", title="Untimed")

        result = get_recent_articles_handler(db=db, limit=3)

        self.assertEqual([row["title"] for row in result], ["New", "Old", "Untimed"])
        self.assertEqual(result[0]["publish_time"], "2024-01-02 08:00:00")
        self.assertEqual(result[0]["status"], "pending")

    def test_get_articles_maps_filters_search_and_pagination(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db = make_database(root)
        seed_article(db, url="https://example.com/alpha", title="Alpha", status="pending")
        seed_article(db, url="https://example.com/beta", title="Beta", status="scraped")
        seed_article(db, url="https://example.com/gamma", title="Gamma", status="scraped")

        result = get_articles_handler(
            db=db,
            status="scraped",
            search="a",
            page=2,
            page_size=1,
            sort_column="title",
            descending=False,
        )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["page_size"], 1)
        self.assertEqual(result["items"], [
            {
                "id": result["items"][0]["id"],
                "url": "https://example.com/gamma",
                "title": "Gamma",
                "publish_time": "",
                "scraped_at": "",
                "file_path": "",
                "status": "scraped",
                "is_empty_content": 1,
            }
        ])


if __name__ == "__main__":
    unittest.main()
