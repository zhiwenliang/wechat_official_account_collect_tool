import unittest

from services.workflows import _remaining_visible_article_click_positions


class FakeCollector:
    config = {
        "windows": {
            "article_list": {
                "article_click_area": {"y": 100},
                "row_height": 20,
                "visible_articles": 3,
            }
        }
    }


class WorkflowTests(unittest.TestCase):
    def test_remaining_visible_article_positions_step_by_row_height(self):
        collector = FakeCollector()

        positions = _remaining_visible_article_click_positions(collector, 3)

        self.assertEqual(positions, [100, 120, 140])
