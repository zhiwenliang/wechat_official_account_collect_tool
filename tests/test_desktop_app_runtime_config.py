from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class DesktopAppRuntimeConfigTests(unittest.TestCase):
    @patch("desktop_backend.app.create_server")
    @patch("desktop_backend.app.configure_runtime_environment")
    def test_main_calls_configure_runtime_before_server_setup(
        self,
        mock_configure: MagicMock,
        mock_create_server: MagicMock,
    ) -> None:
        from desktop_backend import app

        order: list[str] = []

        def track_configure() -> None:
            order.append("configure")

        mock_configure.side_effect = track_configure

        mock_server = MagicMock()
        mock_server.host = "127.0.0.1"
        mock_server.port = 59999

        def track_create_server(**kwargs: object) -> MagicMock:
            order.append("create_server")
            return mock_server

        mock_create_server.side_effect = track_create_server

        app.main(["--port", "59999"])

        mock_configure.assert_called_once_with()
        mock_create_server.assert_called_once()
        self.assertEqual(order, ["configure", "create_server"])


if __name__ == "__main__":
    unittest.main()
