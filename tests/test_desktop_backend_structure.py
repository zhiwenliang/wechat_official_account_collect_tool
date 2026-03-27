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

    def test_tasks_package_re_exports_existing_runtime_objects(self) -> None:
        from desktop_backend.task_events import build_started_event
        from desktop_backend.task_handlers import WorkflowTaskHandlers
        from desktop_backend.task_registry import TaskRegistry

        from desktop_backend.tasks.events import (
            build_started_event as packaged_build_started_event,
        )
        from desktop_backend.tasks.handlers import (
            WorkflowTaskHandlers as packaged_workflow_task_handlers,
        )
        from desktop_backend.tasks.registry import (
            TaskRegistry as packaged_task_registry,
        )

        self.assertIs(build_started_event, packaged_build_started_event)
        self.assertIs(TaskRegistry, packaged_task_registry)
        self.assertIs(WorkflowTaskHandlers, packaged_workflow_task_handlers)
