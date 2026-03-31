import unittest


class DesktopBackendStructureTests(unittest.TestCase):
    def test_package_root_does_not_re_export_migration_article_query_handlers(self) -> None:
        import desktop_backend as desktop_backend_pkg

        self.assertFalse(
            hasattr(desktop_backend_pkg, "get_articles_handler"),
            "import handlers from desktop_backend.articles.query_handlers, not the package root",
        )
        self.assertFalse(
            hasattr(desktop_backend_pkg, "get_recent_articles_handler"),
            "import handlers from desktop_backend.articles.query_handlers, not the package root",
        )
        self.assertFalse(
            hasattr(desktop_backend_pkg, "get_statistics_handler"),
            "import get_statistics_handler from desktop_backend.statistics, not the package root",
        )

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

    def test_task_infrastructure_canonical_imports(self) -> None:
        from desktop_backend.task_events import build_started_event
        from desktop_backend.task_registry import TaskRegistry
        from desktop_backend.tasks.calibration.runtime import default_calibration_runtime_factory
        from desktop_backend.tasks.calibration.status import get_calibration_status_handler
        from desktop_backend.tasks.calibration.worker import CalibrationTaskWorker
        from desktop_backend.tasks.workflow_handlers import WorkflowTaskHandlers

        self.assertTrue(callable(build_started_event))
        self.assertTrue(isinstance(TaskRegistry, type))
        self.assertTrue(isinstance(WorkflowTaskHandlers, type))
        self.assertTrue(callable(default_calibration_runtime_factory))
        self.assertTrue(callable(get_calibration_status_handler))
        self.assertTrue(isinstance(CalibrationTaskWorker, type))

    def test_server_runtime_modules_exist(self) -> None:
        from desktop_backend.server import DesktopBackendServer
        from desktop_backend.server_json import json_bytes
        from desktop_backend.server_routes import register_query_routes
        from desktop_backend.server_runtime import build_request_handler

        self.assertTrue(callable(json_bytes))
        self.assertTrue(callable(register_query_routes))
        self.assertTrue(callable(build_request_handler))
        self.assertTrue(hasattr(DesktopBackendServer, "start"))

    def test_task_handler_split_modules_exist(self) -> None:
        from desktop_backend.tasks.calibration.runtime import (
            default_calibration_runtime_factory as packaged_default_calibration_runtime_factory,
        )
        from desktop_backend.tasks.calibration.status import get_calibration_status_handler
        from desktop_backend.tasks.calibration.worker import CalibrationTaskWorker
        from desktop_backend.tasks.defaults import default_calibration_runtime_factory
        from desktop_backend.tasks.workflow_handlers import WorkflowTaskHandlers

        self.assertTrue(isinstance(WorkflowTaskHandlers, type))
        self.assertTrue(hasattr(WorkflowTaskHandlers, "start_collection_task"))
        self.assertIs(
            default_calibration_runtime_factory,
            packaged_default_calibration_runtime_factory,
        )
        self.assertTrue(callable(get_calibration_status_handler))
        self.assertTrue(hasattr(CalibrationTaskWorker, "submit_response"))

    def test_calibration_package_exports_and_status_handler_identity(self) -> None:
        import desktop_backend.tasks.calibration as calibration_pkg
        from desktop_backend.tasks.calibration import (
            CalibrationTaskWorker,
            DesktopCalibrationRuntime,
            default_calibration_runtime_factory,
            get_calibration_status_handler,
        )
        from desktop_backend.tasks.calibration import runtime as calibration_runtime
        from desktop_backend.tasks.calibration import status as calibration_status
        from desktop_backend.tasks.calibration import worker as calibration_worker

        self.assertEqual(
            set(calibration_pkg.__all__),
            {
                "CalibrationTaskWorker",
                "DesktopCalibrationRuntime",
                "default_calibration_runtime_factory",
                "get_calibration_status_handler",
            },
        )
        self.assertIs(
            get_calibration_status_handler,
            calibration_status.get_calibration_status_handler,
        )
        self.assertIs(CalibrationTaskWorker, calibration_worker.CalibrationTaskWorker)
        self.assertIs(
            DesktopCalibrationRuntime,
            calibration_runtime.DesktopCalibrationRuntime,
        )
        self.assertIs(
            default_calibration_runtime_factory,
            calibration_runtime.default_calibration_runtime_factory,
        )

    def test_database_split_modules_exist(self) -> None:
        from storage.database import Database
        from storage.database_core import connect_db
        from storage.database_mutations import reset_articles_by_ids
        from storage.database_queries import get_articles_by_status

        self.assertTrue(callable(connect_db))
        self.assertTrue(callable(get_articles_by_status))
        self.assertTrue(callable(reset_articles_by_ids))
        self.assertTrue(hasattr(Database, "get_statistics"))

    def test_articles_domain_modules_exist(self) -> None:
        from desktop_backend.articles.command_handlers import (
            delete_selected_articles_handler,
            retry_empty_content_articles_handler,
            retry_failed_articles_handler,
        )
        from desktop_backend.articles.payloads import build_article_payload
        from desktop_backend.articles.query_handlers import (
            MAX_ARTICLES_PAGE_SIZE,
            get_article_detail_handler,
            get_articles_handler,
            get_recent_articles_handler,
        )

        self.assertEqual(MAX_ARTICLES_PAGE_SIZE, 200)
        self.assertTrue(callable(delete_selected_articles_handler))
        self.assertTrue(callable(retry_empty_content_articles_handler))
        self.assertTrue(callable(retry_failed_articles_handler))
        self.assertTrue(callable(build_article_payload))
        self.assertTrue(callable(get_article_detail_handler))
        self.assertTrue(callable(get_articles_handler))
        self.assertTrue(callable(get_recent_articles_handler))

    def test_articles_payloads_module_exports_types_and_builders(self) -> None:
        from desktop_backend.articles.payloads import (
            ArticleDetailPayload,
            ArticlePayload,
            ArticlesPayload,
            RecentArticlePayload,
            build_article_detail_payload,
            build_article_payload,
            build_articles_payload,
            build_recent_article_payload,
        )

        for td in (
            ArticleDetailPayload,
            ArticlePayload,
            ArticlesPayload,
            RecentArticlePayload,
        ):
            self.assertTrue(isinstance(td, type))
        for fn in (
            build_article_detail_payload,
            build_article_payload,
            build_articles_payload,
            build_recent_article_payload,
        ):
            self.assertTrue(callable(fn))

    def test_statistics_module_exports_handler_and_payload_builders(self) -> None:
        from desktop_backend.statistics import (
            StatisticsPayload,
            build_statistics_payload,
            get_statistics_handler,
        )

        self.assertTrue(callable(get_statistics_handler))
        self.assertTrue(callable(build_statistics_payload))
        self.assertTrue(isinstance(StatisticsPayload, type))

    def test_task_domain_runner_modules_exist(self) -> None:
        from desktop_backend.tasks.collection.runner import (
            begin_collection_task,
            run_collection_task,
        )
        from desktop_backend.tasks.scraping.runner import (
            begin_scrape_task,
            run_scrape_task,
        )

        self.assertTrue(callable(begin_collection_task))
        self.assertTrue(callable(run_collection_task))
        self.assertTrue(callable(begin_scrape_task))
        self.assertTrue(callable(run_scrape_task))
