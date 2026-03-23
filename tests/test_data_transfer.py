import sqlite3
import shutil
import unittest
import uuid
import zipfile
from pathlib import Path

from services.data_transfer import export_data_bundle, import_database_file


TEST_TMP_ROOT = Path("tmp_test_workspace")


def make_case_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_articles_db(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            account_name TEXT,
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
    cursor.execute(
        """
        INSERT INTO articles (title, url, status)
        VALUES (?, ?, 'scraped')
        """,
        (title, f"https://example.com/{title}"),
    )
    conn.commit()
    conn.close()


def create_minimal_articles_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
        """
    )
    conn.commit()
    conn.close()


class DataTransferTests(unittest.TestCase):
    def test_export_data_bundle_includes_database_and_article_files(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db_path = root / "data" / "articles.db"
        articles_dir = root / "data" / "articles"
        html_file = articles_dir / "html" / "sample.html"
        md_file = articles_dir / "markdown" / "sample.md"
        zip_path = root / "export.zip"

        create_articles_db(db_path, "source")
        html_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text("<p>html</p>", encoding="utf-8")
        md_file.write_text("# md", encoding="utf-8")

        result = export_data_bundle(zip_path, db_path=db_path, articles_dir=articles_dir)

        self.assertEqual(result.archive_path, zip_path.resolve())
        self.assertEqual(result.file_count, 3)
        self.assertTrue(zip_path.exists())

        with zipfile.ZipFile(zip_path) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [
                    "articles.db",
                    "articles/html/sample.html",
                    "articles/markdown/sample.md",
                ],
            )

    def test_import_database_file_replaces_target_and_creates_backup(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        source_db = root / "incoming.db"
        target_db = root / "runtime" / "articles.db"

        create_articles_db(source_db, "incoming")
        create_articles_db(target_db, "current")

        result = import_database_file(source_db, target_db_path=target_db)

        self.assertEqual(result.target_db_path, target_db.resolve())
        self.assertTrue(result.backup_path is not None)
        self.assertTrue(result.backup_path.exists())
        self.assertEqual(source_db.read_bytes(), target_db.read_bytes())
        self.assertNotEqual(result.backup_path.read_bytes(), target_db.read_bytes())

    def test_import_database_file_rejects_non_article_database(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        source_db = root / "invalid.db"
        target_db = root / "runtime" / "articles.db"

        source_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(source_db)
        conn.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        create_articles_db(target_db, "current")

        with self.assertRaisesRegex(ValueError, "articles"):
            import_database_file(source_db, target_db_path=target_db)

    def test_import_database_file_rejects_articles_table_missing_required_columns(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        source_db = root / "invalid.db"
        target_db = root / "runtime" / "articles.db"

        create_minimal_articles_db(source_db)
        create_articles_db(target_db, "current")

        with self.assertRaisesRegex(ValueError, "缺少必要列"):
            import_database_file(source_db, target_db_path=target_db)

    def test_export_data_bundle_skips_output_archive_inside_articles_directory(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db_path = root / "data" / "articles.db"
        articles_dir = root / "data" / "articles"
        html_file = articles_dir / "html" / "sample.html"
        md_file = articles_dir / "markdown" / "sample.md"
        zip_path = articles_dir / "markdown" / "bundle.zip"

        create_articles_db(db_path, "source")
        html_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text("<p>html</p>", encoding="utf-8")
        md_file.write_text("# md", encoding="utf-8")

        export_data_bundle(zip_path, db_path=db_path, articles_dir=articles_dir)

        with zipfile.ZipFile(zip_path) as archive:
            self.assertNotIn("articles/markdown/bundle.zip", archive.namelist())

    def test_export_data_bundle_rejects_output_path_equal_to_database_path(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        db_path = root / "data" / "articles.db"
        articles_dir = root / "data" / "articles"

        create_articles_db(db_path, "source")

        with self.assertRaisesRegex(ValueError, "不能覆盖当前数据库文件"):
            export_data_bundle(db_path, db_path=db_path, articles_dir=articles_dir)

        conn = sqlite3.connect(db_path)
        title = conn.execute("SELECT title FROM articles").fetchone()[0]
        conn.close()
        self.assertEqual(title, "source")


if __name__ == "__main__":
    unittest.main()
