import unittest

from scraper.content_scraper import ContentScraper


class FakeLocator:
    def __init__(self, texts):
        self._texts = texts

    def count(self):
        return len(self._texts)

    @property
    def first(self):
        return self

    def inner_text(self):
        return self._texts[0]


class FakePage:
    def __init__(self, selector_map):
        self.selector_map = selector_map

    def locator(self, selector):
        return FakeLocator(self.selector_map.get(selector, []))


class ContentScraperTests(unittest.TestCase):
    def test_extract_account_name_prefers_js_name(self):
        scraper = ContentScraper()
        page = FakePage(
            {
                "#js_name": ["PaperAgent"],
                "#profileBt a": ["FallbackName"],
            }
        )

        account_name = scraper._extract_account_name(page)

        self.assertEqual(account_name, "PaperAgent")

    def test_extract_account_name_falls_back_to_profile_link(self):
        scraper = ContentScraper()
        page = FakePage(
            {
                "#profileBt a": ["PaperAgent"],
            }
        )

        account_name = scraper._extract_account_name(page)

        self.assertEqual(account_name, "PaperAgent")

    def test_extract_account_name_returns_empty_string_when_missing(self):
        scraper = ContentScraper()
        page = FakePage({})

        account_name = scraper._extract_account_name(page)

        self.assertEqual(account_name, "")
