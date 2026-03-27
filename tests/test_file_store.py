import shutil
import unittest
import uuid
from pathlib import Path

from storage.file_store import FileStore


TEST_TMP_ROOT = Path("tmp_test_workspace")


def make_case_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    root = TEST_TMP_ROOT / f"case_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


class FileStoreTests(unittest.TestCase):
    def test_delete_article_files_ignores_file_paths_outside_managed_directory(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        base_dir = root / "data" / "articles"
        outside_file = root / "outside.html"
        outside_file.write_text("keep", encoding="utf-8")
        store = FileStore(base_dir=base_dir)

        removed = store.delete_article_files(
            {
                "file_path": str(outside_file),
                "title": "example",
                "publish_time": "2026-03-21T10:00:00",
            }
        )

        self.assertEqual(removed, [])
        self.assertTrue(outside_file.exists())

    def test_save_article_avoids_overwriting_same_timestamp_and_title(self):
        root = make_case_root()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        store = FileStore(base_dir=root / "data" / "articles")

        first_path = store.save_article(
            {
                "title": "Same Title",
                "url": "https://example.com/articles/1",
                "publish_time": "2026-03-22T10:00:00",
                "content_html": "<p>first</p>",
            },
            content_markdown="# first",
        )
        second_path = store.save_article(
            {
                "title": "Same Title",
                "url": "https://example.com/articles/2",
                "publish_time": "2026-03-22T10:00:00",
                "content_html": "<p>second</p>",
            },
            content_markdown="# second",
        )

        self.assertNotEqual(first_path, second_path)
        self.assertEqual(len(list(store.html_dir.glob("*.html"))), 2)
        self.assertEqual(len(list(store.md_dir.glob("*.md"))), 2)
        self.assertEqual(Path(first_path).read_text(encoding="utf-8").count("first"), 1)
        self.assertEqual(Path(second_path).read_text(encoding="utf-8").count("second"), 1)

