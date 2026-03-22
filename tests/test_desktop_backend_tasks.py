import unittest

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


if __name__ == "__main__":
    unittest.main()
