import shutil
import sqlite3
import unittest
import uuid
from pathlib import Path

from desktop_backend.articles.command_handlers import delete_selected_articles_handler
from desktop_backend.articles.query_handlers import (
    get_articles_handler,
    get_recent_articles_handler,
)
from desktop_backend.query_handlers import (
    get_article_detail_handler,
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

    def test_get_article_detail_handler_returns_payload_for_existing_article(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db = make_database(root)
        seed_article(
            db,
            url="https://example.com/detail",
            title="Detail Title",
            status="scraped",
            publish_time="2024-03-01 12:00:00",
            scraped_at="2024-03-02 10:00:00",
            file_path="/articles/detail.md",
            content_html="<p>body</p>",
            content_markdown="# Hello",
        )
        conn = sqlite3.connect(db.db_path)
        try:
            row = conn.execute(
                "SELECT id FROM articles WHERE url = ?",
                ("https://example.com/detail",),
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        article_id = int(row[0])

        result = get_article_detail_handler(db=db, article_id=article_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], article_id)
        self.assertEqual(result["url"], "https://example.com/detail")
        self.assertEqual(result["title"], "Detail Title")
        self.assertEqual(result["publish_time"], "2024-03-01 12:00:00")
        self.assertEqual(result["scraped_at"], "2024-03-02 10:00:00")
        self.assertEqual(result["file_path"], "/articles/detail.md")
        self.assertEqual(result["status"], "scraped")
        self.assertEqual(result["is_empty_content"], 0)
        self.assertEqual(result["content_markdown"], "# Hello")

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

    def test_get_articles_clamps_page_size_to_maximum(self):
        class FakeDatabase:
            def __init__(self):
                self.limit = None
                self.offset = None

            def get_articles_by_status(self, **kwargs):
                self.limit = kwargs["limit"]
                self.offset = kwargs["offset"]
                return []

            def count_articles(self, **_kwargs):
                return 0

        db = FakeDatabase()

        result = get_articles_handler(db=db, page=2, page_size=1000)

        self.assertEqual(result["page"], 2)
        self.assertEqual(result["page_size"], 200)
        self.assertEqual(db.limit, 200)
        self.assertEqual(db.offset, 200)

    def test_delete_selected_articles_uses_targeted_id_lookup(self):
        class FakeDatabase:
            def __init__(self):
                self.loaded_ids = None
                self.deleted_ids = None

            def get_articles_by_ids(self, article_ids):
                self.loaded_ids = list(article_ids)
                return [
                    (2, "https://example.com/two", "Two", "", "", "", "pending", 1),
                    (5, "https://example.com/five", "Five", "", "", "", "pending", 1),
                ]

            def delete_articles_by_ids(self, article_ids):
                self.deleted_ids = list(article_ids)
                return len(article_ids)

            def get_articles_by_status(self, **_kwargs):
                raise AssertionError("delete handler should not scan all articles")

        class FakeFileStore:
            def __init__(self):
                self.deleted_titles = []

            def delete_article_files(self, article_data):
                self.deleted_titles.append(article_data["title"])
                return [f"/tmp/{article_data['id']}.html"]

        db = FakeDatabase()
        file_store = FakeFileStore()

        result = delete_selected_articles_handler(
            article_ids=[5, 2, 5],
            db=db,
            file_store=file_store,
        )

        self.assertEqual(db.loaded_ids, [5, 2])
        self.assertEqual(db.deleted_ids, [5, 2])
        self.assertEqual(file_store.deleted_titles, ["Two", "Five"])
        self.assertEqual(result["deleted"], 2)
        self.assertEqual(result["removed_files"], 2)
        self.assertEqual(result["file_errors"], [])


if __name__ == "__main__":
    unittest.main()
