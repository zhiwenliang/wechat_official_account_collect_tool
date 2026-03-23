import shutil
import sqlite3
import unittest
import uuid
from pathlib import Path

from storage.database import Database


TEST_TMP_ROOT = Path("tmp_test_workspace")


def make_case_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


class DatabaseAccountNameTests(unittest.TestCase):
    def test_database_migrates_account_name_column(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db_path = root / "articles.db"

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE NOT NULL,
                publish_time TEXT,
                scraped_at TEXT,
                status TEXT DEFAULT 'pending',
                file_path TEXT,
                content_html TEXT,
                content_markdown TEXT
            )
            """
        )
        conn.commit()
        conn.close()

        Database(db_path)

        conn = sqlite3.connect(db_path)
        columns = [row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()]
        conn.close()
        self.assertIn("account_name", columns)
