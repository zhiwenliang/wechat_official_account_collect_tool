import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import main


class MainCliTests(unittest.TestCase):
    def test_generate_index_uses_console_safe_success_text(self):
        buffer = io.StringIO()
        with patch("main.generate_article_index", return_value="INDEX.md"), redirect_stdout(buffer):
            main.generate_index()

        self.assertEqual(buffer.getvalue().strip(), "索引已生成: INDEX.md")

    def test_main_returns_error_for_unknown_command(self):
        with patch("sys.argv", ["main.py", "unknown"]):
            result = main.main()

        self.assertEqual(result, 1)

