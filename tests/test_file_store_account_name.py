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


class FileStoreAccountNameTests(unittest.TestCase):
    def test_render_markdown_includes_account_name(self):
        store = FileStore(base_dir=make_case_root() / "articles")
        self.addCleanup(lambda: shutil.rmtree(store.base_dir.parent, ignore_errors=True))

        markdown = store.render_markdown(
            {
                "title": "示例文章",
                "account_name": "PaperAgent",
                "publish_time": "2026-03-22T10:00:00",
                "url": "https://example.com/article",
                "content_html": "<p>正文</p>",
            }
        )

        self.assertIn("**公众号**: PaperAgent", markdown)

    def test_generate_html_includes_account_name(self):
        store = FileStore(base_dir=make_case_root() / "articles")
        self.addCleanup(lambda: shutil.rmtree(store.base_dir.parent, ignore_errors=True))

        html = store._generate_html(
            {
                "title": "示例文章",
                "account_name": "PaperAgent",
                "publish_time": "2026-03-22T10:00:00",
                "url": "https://example.com/article",
                "content_html": "<p>正文</p>",
            }
        )

        self.assertIn("公众号: PaperAgent", html)
