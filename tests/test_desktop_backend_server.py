import json
import time
import unittest
import urllib.request

from desktop_backend.server import DesktopBackendServer


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


if __name__ == "__main__":
    unittest.main()
