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

