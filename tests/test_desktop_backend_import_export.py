import json
import shutil
import sqlite3
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import utils.runtime_env as runtime_env
from desktop_backend.app import create_server
from storage.database import Database
from storage.file_store import FileStore


TEST_TMP_ROOT = Path("tmp_test_workspace")


def make_case_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


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
) -> int:
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
    article_id = cursor.lastrowid
    conn.close()
    return article_id


def create_source_database(path: Path, *, title: str, url: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
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
    cursor.execute(
        """
        INSERT INTO articles (
            title, url, publish_time, scraped_at, status,
            file_path, content_html, content_markdown
        )
        VALUES (?, ?, '', '', 'scraped', '', '<p>source</p>', '# source')
        """,
        (title, url),
    )
    conn.commit()
    conn.close()


def post_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class DesktopBackendImportExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self._original_runtime_root = runtime_env.REPO_ROOT
        runtime_env.REPO_ROOT = self.root
        self.addCleanup(self._restore_runtime_root)

    def test_retry_failed_articles_endpoint_resets_failed_rows(self):
        db = Database()
        seed_article(db, url="https://example.com/failed", title="Failed", status="failed")
        seed_article(db, url="https://example.com/pending", title="Pending", status="pending")

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(f"http://{server.host}:{server.port}/api/articles/retry-failed")

        self.assertEqual(status_code, 200)
        self.assertEqual(payload, {"status": "ok", "affected": 1})
        self.assertEqual(db.get_statistics()["failed"], 0)
        self.assertEqual(db.get_article_status("https://example.com/failed"), "pending")

    def test_retry_empty_content_articles_endpoint_resets_empty_rows(self):
        db = Database()
        seed_article(
            db,
            url="https://example.com/empty",
            title="Empty",
            status="scraped",
            scraped_at="2024-01-01 09:00:00",
            file_path="data/articles/html/empty.html",
            content_html="",
            content_markdown="",
        )
        seed_article(
            db,
            url="https://example.com/full",
            title="Full",
            status="scraped",
            scraped_at="2024-01-01 09:00:00",
            file_path="data/articles/html/full.html",
            content_html="<p>content</p>",
            content_markdown="# content",
        )

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(f"http://{server.host}:{server.port}/api/articles/retry-empty-content")

        self.assertEqual(status_code, 200)
        self.assertEqual(payload, {"status": "ok", "affected": 1})

        conn = sqlite3.connect(db.db_path)
        row = conn.execute(
            """
            SELECT status, scraped_at, file_path, content_html, content_markdown
            FROM articles
            WHERE url = ?
            """,
            ("https://example.com/empty",),
        ).fetchone()
        conn.close()

        self.assertEqual(row, ("pending", None, None, None, None))

    def test_delete_selected_articles_endpoint_removes_database_rows_and_files(self):
        db = Database()
        file_store = FileStore()
        article_id = seed_article(
            db,
            url="https://example.com/delete",
            title="Delete Me",
            status="scraped",
            publish_time="2024-01-01 08:00:00",
            scraped_at="2024-01-01 09:00:00",
            file_path=str(file_store.html_dir / "20240101_080000_Delete Me.html"),
            content_html="<p>content</p>",
            content_markdown="# content",
        )
        html_path = file_store.html_dir / "20240101_080000_Delete Me.html"
        md_path = file_store.md_dir / "20240101_080000_Delete Me.md"
        html_path.write_text("<p>content</p>", encoding="utf-8")
        md_path.write_text("# content", encoding="utf-8")

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(
            f"http://{server.host}:{server.port}/api/articles/delete",
            {"article_ids": [article_id]},
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload, {"status": "ok", "deleted": 1, "removed_files": 2, "file_errors": []})
        self.assertFalse(html_path.exists())
        self.assertFalse(md_path.exists())
        self.assertEqual(db.count_articles(), 0)

    def test_export_data_bundle_endpoint_writes_zip_from_runtime_paths(self):
        db = Database()
        file_store = FileStore()
        seed_article(
            db,
            url="https://example.com/export",
            title="Export",
            status="scraped",
            publish_time="2024-01-01 08:00:00",
            scraped_at="2024-01-01 09:00:00",
            file_path=str(file_store.html_dir / "20240101_080000_Export.html"),
            content_html="<p>content</p>",
            content_markdown="# content",
        )
        (file_store.html_dir / "20240101_080000_Export.html").write_text("<p>content</p>", encoding="utf-8")
        (file_store.md_dir / "20240101_080000_Export.md").write_text("# content", encoding="utf-8")
        output_path = self.root / "bundle.zip"

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(
            f"http://{server.host}:{server.port}/api/data/export",
            {"output_path": str(output_path)},
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(Path(payload["archive_path"]), output_path.resolve())
        self.assertEqual(payload["file_count"], 3)
        self.assertTrue(output_path.exists())

    def test_export_data_bundle_endpoint_rejects_runtime_database_path_as_output(self):
        current_db = Database()
        seed_article(current_db, url="https://example.com/current", title="Current", status="pending")

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(
            f"http://{server.host}:{server.port}/api/data/export",
            {"output_path": str(current_db.db_path)},
        )

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertIn("不能覆盖当前数据库文件", payload["message"])

        conn = sqlite3.connect(current_db.db_path)
        title = conn.execute("SELECT title FROM articles").fetchone()[0]
        conn.close()
        self.assertEqual(title, "Current")

    def test_import_database_endpoint_replaces_runtime_database_and_keeps_backup(self):
        current_db = Database()
        seed_article(current_db, url="https://example.com/current", title="Current", status="pending")
        source_db = self.root / "incoming.db"
        create_source_database(source_db, title="Incoming", url="https://example.com/incoming")

        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(
            f"http://{server.host}:{server.port}/api/data/import",
            {"source_db_path": str(source_db)},
        )

        self.assertEqual(status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(Path(payload["source_db_path"]), source_db.resolve())
        self.assertEqual(Path(payload["target_db_path"]), current_db.db_path.resolve())
        self.assertIsNotNone(payload["backup_path"])

        backup_path = Path(payload["backup_path"])
        self.assertTrue(backup_path.exists())

        conn = sqlite3.connect(current_db.db_path)
        titles = [row[0] for row in conn.execute("SELECT title FROM articles ORDER BY id").fetchall()]
        conn.close()

        self.assertEqual(titles, ["Incoming"])

    def test_import_database_endpoint_returns_400_for_missing_source_db(self):
        server = create_server(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        status_code, payload = post_json(
            f"http://{server.host}:{server.port}/api/data/import",
            {"source_db_path": str(self.root / "missing.db")},
        )

        self.assertEqual(status_code, 400)
        self.assertEqual(payload["status"], "error")
        self.assertIn("数据库文件不存在", payload["message"])

    def _restore_runtime_root(self) -> None:
        runtime_env.REPO_ROOT = self._original_runtime_root


if __name__ == "__main__":
    unittest.main()
