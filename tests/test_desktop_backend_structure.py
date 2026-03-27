import unittest


class DesktopBackendStructureTests(unittest.TestCase):
    def test_http_helper_modules_exist(self) -> None:
        from desktop_backend.http.image_proxy import (
            IMAGE_PROXY_MAX_BYTES,
            validate_image_proxy_url,
        )
        from desktop_backend.http.parsing import parse_bool, parse_int

        self.assertEqual(parse_int({"page": ["7"]}, "page", 1), 7)
        self.assertTrue(parse_bool({"descending": ["true"]}, "descending"))
        self.assertEqual(
            validate_image_proxy_url("https://mmbiz.qpic.cn/image.png"),
            "https://mmbiz.qpic.cn/image.png",
        )
        self.assertEqual(IMAGE_PROXY_MAX_BYTES, 5 * 1024 * 1024)
