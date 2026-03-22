import os
import socket
import sqlite3
import json
import shutil
import time
import unittest
from pathlib import Path
from urllib.parse import urlencode
import urllib.request
import uuid

from desktop_backend.runtime import select_runtime_port
from desktop_backend.server import DesktopBackendServer
from storage.database import Database


def make_database(root: Path) -> Database:
    return Database(root / "articles.db")


def make_case_root() -> Path:
    root = Path("tmp_test_workspace")
    root.mkdir(parents=True, exist_ok=True)
    case_root = root / f"case_{uuid.uuid4().hex}"
    case_root.mkdir(parents=True, exist_ok=True)
    return case_root


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


def read_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=1) as response:
        return json.loads(response.read().decode("utf-8"))


class DesktopBackendServerTests(unittest.TestCase):
    def test_health_endpoint_returns_ok_payload(self):
        server = DesktopBackendServer(host="127.0.0.1", port=0)
        server.start()
        self.addCleanup(server.stop)

        deadline = time.time() + 5
        url = f"http://{server.host}:{server.port}/health"

        while True:
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except OSError:
                if time.time() >= deadline:
                    raise
                time.sleep(0.05)

        self.assertEqual(
            payload,
            {
                "status": "ok",
                "service": "desktop-backend",
            },
        )

    def test_select_runtime_port_ignores_invalid_env_port_when_preferred_port_is_valid(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            preferred_port = sock.getsockname()[1]

        original_env_port = os.environ.get("DESKTOP_BACKEND_PORT")
        os.environ["DESKTOP_BACKEND_PORT"] = "-1"
        self.addCleanup(self._restore_env_port, original_env_port)

        selected_port = select_runtime_port(host="127.0.0.1", preferred_port=preferred_port)

        self.assertEqual(selected_port, preferred_port)

    def test_statistics_route_returns_json_over_http(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        db = make_database(root)
        seed_article(db, url="https://example.com/1", title="Alpha", status="pending")
        seed_article(db, url="https://example.com/2", title="Beta", status="scraped")

        server = DesktopBackendServer(host="127.0.0.1", port=0, db=db)
        server.start()
        self.addCleanup(server.stop)

        payload = self._wait_for_json(
            f"http://{server.host}:{server.port}/api/statistics",
        )

        self.assertEqual(
            payload,
            {
                "total": 2,
                "pending": 1,
                "scraped": 1,
                "failed": 0,
                "empty_content": 1,
                "failed_urls": [],
            },
        )

    def test_recent_articles_route_clamps_invalid_limit_over_http(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        db = make_database(root)
        seed_article(db, url="https://example.com/old", title="Old", publish_time="2024-01-01 08:00:00")
        seed_article(db, url="https://example.com/new", title="New", publish_time="2024-01-02 08:00:00")

        server = DesktopBackendServer(host="127.0.0.1", port=0, db=db)
        server.start()
        self.addCleanup(server.stop)

        payload = self._wait_for_json(
            f"http://{server.host}:{server.port}/api/recent-articles?limit=-1",
        )

        self.assertEqual(
            payload,
            [
                {
                    "id": payload[0]["id"],
                    "title": "New",
                    "publish_time": "2024-01-02 08:00:00",
                    "status": "pending",
                    "is_empty_content": 0,
                }
            ],
        )

    def test_articles_route_parses_query_string_over_http(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))

        db = make_database(root)
        seed_article(db, url="https://example.com/alpha", title="Alpha", status="pending")
        seed_article(db, url="https://example.com/beta", title="Beta", status="scraped")
        seed_article(db, url="https://example.com/gamma", title="阿尔法", status="scraped")

        server = DesktopBackendServer(host="127.0.0.1", port=0, db=db)
        server.start()
        self.addCleanup(server.stop)

        query = urlencode(
            {
                "status": "scraped",
                "search": "a",
                "page": 2,
                "page_size": 1,
                "sort_column": "title",
                "descending": "false",
            }
        )
        payload = self._wait_for_json(
            f"http://{server.host}:{server.port}/api/articles?{query}",
        )

        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 1)
        self.assertEqual(payload["items"], [
            {
                "id": payload["items"][0]["id"],
                "url": "https://example.com/gamma",
                "title": "阿尔法",
                "publish_time": "",
                "scraped_at": "",
                "file_path": "",
                "status": "scraped",
                "is_empty_content": 1,
            }
        ])

    def _wait_for_json(self, url: str):
        deadline = time.time() + 5

        while True:
            try:
                return read_json(url)
            except OSError:
                if time.time() >= deadline:
                    raise
                time.sleep(0.05)

    def _restore_env_port(self, value: str | None) -> None:
        if value is None:
            os.environ.pop("DESKTOP_BACKEND_PORT", None)
        else:
            os.environ["DESKTOP_BACKEND_PORT"] = value


if __name__ == "__main__":
    unittest.main()
