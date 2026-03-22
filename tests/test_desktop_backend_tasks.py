import json
import time
import unittest
import urllib.request
import urllib.error

from desktop_backend.app import create_server

from desktop_backend.task_events import (
    build_cancelled_event,
    build_completed_event,
    build_error_event,
    build_log_event,
    build_progress_event,
    build_started_event,
    build_status_event,
    build_stopped_event,
)
from desktop_backend.task_registry import TaskRegistry


class FakeCollectionDatabase:
    db_path = "fake-articles.db"

    def __init__(self) -> None:
        self.saved_links: list[str] = []

    def add_article(self, link: str):
        self.saved_links.append(link)
        return len(self.saved_links)


class FakeCollector:
    def __init__(self) -> None:
        self.config = {
            "windows": {
                "article_list": {
                    "article_click_area": {"y": 100},
                    "visible_articles": 0,
                }
            },
            "collection": {
                "max_articles": 1,
            },
        }
        self.db = FakeCollectionDatabase()
        self.collected_links = set()
        self.recent_links = []

    def should_stop(self) -> bool:
        return False

    def click_article(self, _click_y: int) -> bool:
        return True

    def collect_link(self) -> str:
        return "https://example.com/collected"

    def _check_duplicate_count(self) -> int:
        return 0

    def refresh_scroll(self) -> bool:
        return True

    def close_tabs(self) -> bool:
        return True

    def scroll_article(self) -> bool:
        return True


class BlockingCollector(FakeCollector):
    def __init__(self) -> None:
        super().__init__()
        self.stop_observed = False

    def click_article(self, _click_y: int) -> bool:
        deadline = time.time() + 2
        while time.time() < deadline:
            if self.should_stop():
                self.stop_observed = True
                return False
            time.sleep(0.01)
        return True


class FakeScrapeDatabase:
    def __init__(self) -> None:
        self.updated: list[tuple[str, dict]] = []

    def get_article_status(self, _url: str) -> str:
        return "pending"

    def update_article(self, url: str, **kwargs) -> None:
        self.updated.append((url, kwargs))


class FakeFileStore:
    def render_markdown(self, article_data: dict) -> str:
        return f"# {article_data['title']}"

    def save_article(self, article_data: dict, *, content_markdown: str) -> str:
        return f"markdown/{article_data['title']}.md"

    def generate_index(self) -> str:
        return "markdown/INDEX.md"


class FakeScraper:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def should_stop(self) -> bool:
        return False

    def scrape_article(self, url: str):
        return {
            "title": "Article One",
            "publish_time": "2024-01-01 08:00:00",
            "scraped_at": "2024-01-01 09:00:00",
            "content_html": f"<p>{url}</p>",
        }


class BlockingScraper(FakeScraper):
    def __init__(self) -> None:
        super().__init__()
        self.stop_called = False

    def stop(self) -> None:
        self.stop_called = True
        self.stopped = True

    def should_stop(self) -> bool:
        return self.stop_called

    def scrape_article(self, url: str):
        deadline = time.time() + 2
        while time.time() < deadline:
            if self.should_stop():
                return None
            time.sleep(0.01)
        return super().scrape_article(url)


class NonIdempotentStopScraper(BlockingScraper):
    def __init__(self) -> None:
        super().__init__()
        self.stop_count = 0

    def stop(self) -> None:
        self.stop_count += 1
        if self.stop_count > 1:
            raise RuntimeError("stop called more than once")
        super().stop()


def post_json(url: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


class DesktopBackendTaskTests(unittest.TestCase):
    def test_task_registry_start_task_creates_task_id(self):
        registry = TaskRegistry()

        task_id = registry.start_task("collection")

        self.assertIsInstance(task_id, str)
        self.assertTrue(task_id)
        self.assertTrue(registry.is_active(task_id))

    def test_task_registry_buffers_events_in_order(self):
        registry = TaskRegistry()
        task_id = registry.start_task("scraping")

        registry.record_progress(task_id, 1, 10, "step 1")
        registry.record_log(task_id, "first log")
        registry.record_log(task_id, "second log")

        events = registry.drain_events(task_id)

        self.assertEqual(
            [event["type"] for event in events],
            ["started", "progress", "log", "log"],
        )
        self.assertEqual(events[1]["current"], 1)
        self.assertEqual(events[1]["total"], 10)
        self.assertEqual(events[2]["message"], "first log")
        self.assertEqual(events[3]["message"], "second log")

    def test_task_registry_marks_task_stopping(self):
        registry = TaskRegistry()
        task_id = registry.start_task("collection")

        registry.request_stop(task_id)

        self.assertTrue(registry.should_stop(task_id))
        self.assertTrue(registry.is_stopping(task_id))

    def test_task_registry_completion_clears_active_state(self):
        registry = TaskRegistry()
        task_id = registry.start_task("collection")

        registry.complete_task(task_id)

        self.assertFalse(registry.is_active(task_id))
        self.assertIsNone(registry.get_task(task_id))

    def test_task_registry_stopped_event_finalizes_task(self):
        registry = TaskRegistry()
        task_id = registry.start_task("collection")

        registry.record_stopped(task_id, "user requested")

        self.assertFalse(registry.is_active(task_id))
        self.assertIsNone(registry.get_task(task_id))
        self.assertEqual(
            [event["type"] for event in registry.drain_events(task_id)],
            ["started", "stopped"],
        )

    def test_get_task_returns_copy_of_internal_state(self):
        registry = TaskRegistry()
        task_id = registry.start_task("collection")

        snapshot = registry.get_task(task_id)

        self.assertIsNotNone(snapshot)
        snapshot.stopping = True
        snapshot.events.append({"type": "log", "task_id": task_id, "message": "mutated"})

        fresh = registry.get_task(task_id)
        self.assertIsNotNone(fresh)
        self.assertFalse(fresh.stopping)
        self.assertEqual([event["type"] for event in fresh.events], ["started"])

    def test_event_builders_normalize_payloads(self):
        self.assertEqual(
            build_started_event(task_id="task-1", task_type="collection"),
            {
                "type": "started",
                "task_id": "task-1",
                "task_type": "collection",
            },
        )
        self.assertEqual(
            build_log_event(task_id="task-1", message=None),
            {
                "type": "log",
                "task_id": "task-1",
                "message": "",
            },
        )
        self.assertEqual(
            build_progress_event(task_id="task-1", current="3", total="7", message=None),
            {
                "type": "progress",
                "task_id": "task-1",
                "current": 3,
                "total": 7,
                "message": "",
            },
        )
        self.assertEqual(
            build_status_event(task_id="task-1", status=None, message="hello"),
            {
                "type": "status",
                "task_id": "task-1",
                "status": "",
                "message": "hello",
            },
        )
        self.assertEqual(
            build_completed_event(task_id="task-1", task_type="collection"),
            {
                "type": "completed",
                "task_id": "task-1",
                "task_type": "collection",
            },
        )
        self.assertEqual(
            build_error_event(task_id="task-1", message=None),
            {
                "type": "error",
                "task_id": "task-1",
                "message": "",
            },
        )
        self.assertEqual(
            build_stopped_event(task_id="task-1", reason=None),
            {
                "type": "stopped",
                "task_id": "task-1",
                "reason": "",
            },
        )
        self.assertEqual(
            build_cancelled_event(task_id="task-1", reason="user"),
            {
                "type": "cancelled",
                "task_id": "task-1",
                "reason": "user",
            },
        )

    def test_collection_task_route_emits_started_log_and_completed_events(self):
        server = create_server(host="127.0.0.1", port=0, collector_factory=FakeCollector)
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/collection")
        task_id = payload["task_id"]

        self._wait_for_task_completion(server.task_registry, task_id)
        events = server.task_registry.drain_events(task_id)

        self.assertEqual(events[0]["type"], "started")
        self.assertEqual(events[0]["task_type"], "collection")
        self.assertIn("log", [event["type"] for event in events])
        self.assertEqual(events[-1]["type"], "completed")

    def test_collection_task_route_surfaces_workflow_logs_as_log_events(self):
        server = create_server(host="127.0.0.1", port=0, collector_factory=FakeCollector)
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/collection")
        task_id = payload["task_id"]

        self._wait_for_task_completion(server.task_registry, task_id)
        events = server.task_registry.drain_events(task_id)
        log_messages = [event["message"] for event in events if event["type"] == "log"]

        self.assertTrue(any("开始采集" in message for message in log_messages))
        self.assertTrue(any("已保存" in message for message in log_messages))

    def test_scrape_task_route_surfaces_progress_events(self):
        server = create_server(
            host="127.0.0.1",
            port=0,
            scraper_factory=FakeScraper,
            scrape_db_factory=FakeScrapeDatabase,
            file_store_factory=FakeFileStore,
            pending_articles_provider=lambda: [(1, "https://example.com/article-1")],
        )
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/scrape")
        task_id = payload["task_id"]

        self._wait_for_task_completion(server.task_registry, task_id)
        events = server.task_registry.drain_events(task_id)
        progress_events = [event for event in events if event["type"] == "progress"]

        self.assertEqual(len(progress_events), 1)
        self.assertEqual(progress_events[0]["current"], 1)
        self.assertEqual(progress_events[0]["total"], 1)
        self.assertEqual(progress_events[0]["message"], "已处理 1/1 篇")

    def test_stop_route_honors_workflow_stop_checker(self):
        holders: list[BlockingCollector] = []

        def collector_factory():
            collector = BlockingCollector()
            holders.append(collector)
            return collector

        server = create_server(host="127.0.0.1", port=0, collector_factory=collector_factory)
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/collection")
        task_id = payload["task_id"]

        stop_payload = post_json(f"http://{server.host}:{server.port}/tasks/{task_id}/stop")

        self.assertEqual(stop_payload["task_id"], task_id)
        self.assertTrue(stop_payload["stopping"])

        self._wait_for_task_completion(server.task_registry, task_id)
        events = server.task_registry.drain_events(task_id)

        self.assertTrue(holders[0].stop_observed)
        self.assertEqual(events[-1]["type"], "stopped")

    def test_scrape_stop_route_calls_scraper_stop(self):
        holders: list[BlockingScraper] = []

        def scraper_factory():
            scraper = BlockingScraper()
            holders.append(scraper)
            return scraper

        server = create_server(
            host="127.0.0.1",
            port=0,
            scraper_factory=scraper_factory,
            scrape_db_factory=FakeScrapeDatabase,
            file_store_factory=FakeFileStore,
            pending_articles_provider=lambda: [(1, "https://example.com/article-1")],
        )
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/scrape")
        task_id = payload["task_id"]

        stop_payload = post_json(f"http://{server.host}:{server.port}/tasks/{task_id}/stop")

        self.assertEqual(stop_payload["task_id"], task_id)
        self.assertTrue(stop_payload["stopping"])
        self._wait_for_task_completion(server.task_registry, task_id)

        events = server.task_registry.drain_events(task_id)
        self.assertTrue(holders[0].stop_called)
        self.assertEqual(events[-1]["type"], "stopped")

    def test_scrape_stop_route_tolerates_non_idempotent_scraper_stop(self):
        holders: list[NonIdempotentStopScraper] = []

        def scraper_factory():
            scraper = NonIdempotentStopScraper()
            holders.append(scraper)
            return scraper

        server = create_server(
            host="127.0.0.1",
            port=0,
            scraper_factory=scraper_factory,
            scrape_db_factory=FakeScrapeDatabase,
            file_store_factory=FakeFileStore,
            pending_articles_provider=lambda: [(1, "https://example.com/article-1")],
        )
        server.start()
        self.addCleanup(server.stop)

        payload = post_json(f"http://{server.host}:{server.port}/tasks/scrape")
        task_id = payload["task_id"]

        stop_payload = post_json(f"http://{server.host}:{server.port}/tasks/{task_id}/stop")

        self.assertEqual(stop_payload["task_id"], task_id)
        self.assertTrue(stop_payload["stopping"])
        self._wait_for_task_completion(server.task_registry, task_id)

        events = server.task_registry.drain_events(task_id)
        self.assertEqual(holders[0].stop_count, 1)
        self.assertEqual(events[-1]["type"], "stopped")

    def test_task_route_returns_json_error_when_factory_fails(self):
        def bad_collector_factory():
            raise RuntimeError("collector unavailable")

        server = create_server(host="127.0.0.1", port=0, collector_factory=bad_collector_factory)
        server.start()
        self.addCleanup(server.stop)

        request = urllib.request.Request(
            f"http://{server.host}:{server.port}/tasks/collection",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=2)

        self.assertEqual(context.exception.code, 500)
        payload = json.loads(context.exception.read().decode("utf-8"))
        self.assertEqual(payload["status"], "error")
        self.assertIn("collector unavailable", payload["message"])
        self.assertEqual(server.task_registry._tasks, {})

    def test_task_route_returns_json_error_for_invalid_json(self):
        server = create_server(host="127.0.0.1", port=0, collector_factory=FakeCollector)
        server.start()
        self.addCleanup(server.stop)

        request = urllib.request.Request(
            f"http://{server.host}:{server.port}/tasks/collection",
            data=b"{invalid",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=2)

        self.assertEqual(context.exception.code, 400)
        payload = json.loads(context.exception.read().decode("utf-8"))
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["message"], "invalid json body")

    def _wait_for_task_completion(self, registry: TaskRegistry, task_id: str) -> None:
        deadline = time.time() + 5
        while registry.is_active(task_id):
            if time.time() >= deadline:
                self.fail(f"task {task_id} did not complete in time")
            time.sleep(0.02)


if __name__ == "__main__":
    unittest.main()
