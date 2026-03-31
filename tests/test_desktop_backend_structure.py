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
        from desktop_backend.task_handlers import WorkflowTaskHandlers
        from desktop_backend.tasks.calibration.runtime import (
            default_calibration_runtime_factory as packaged_default_calibration_runtime_factory,
        )
        from desktop_backend.tasks.calibration.status import get_calibration_status_handler
        from desktop_backend.tasks.calibration.worker import (
            CalibrationTaskWorker as packaged_calibration_task_worker,
        )
        from desktop_backend.tasks.calibration_worker import CalibrationTaskWorker
        from desktop_backend.tasks.defaults import default_calibration_runtime_factory
        from desktop_backend.tasks.workflow_handlers_impl import WorkflowTaskHandlersImpl

        self.assertIs(WorkflowTaskHandlers, WorkflowTaskHandlersImpl)
        self.assertIs(CalibrationTaskWorker, packaged_calibration_task_worker)
        self.assertIs(
            default_calibration_runtime_factory,
            packaged_default_calibration_runtime_factory,
        )
        self.assertTrue(callable(get_calibration_status_handler))
        self.assertTrue(hasattr(CalibrationTaskWorker, "submit_response"))

    def test_calibration_package_exports_and_status_handler_identity(self) -> None:
        import desktop_backend.query_handlers as query_handlers
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
        self.assertIs(
            query_handlers.get_calibration_status_handler,
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
        from desktop_backend.articles.command_handlers import delete_selected_articles_handler
        from desktop_backend.articles.payloads import build_article_payload
        from desktop_backend.articles.query_handlers import (
            MAX_ARTICLES_PAGE_SIZE,
            get_article_detail_handler,
            get_articles_handler,
            get_recent_articles_handler,
        )

        self.assertEqual(MAX_ARTICLES_PAGE_SIZE, 200)
        self.assertTrue(callable(delete_selected_articles_handler))
        self.assertTrue(callable(build_article_payload))
        self.assertTrue(callable(get_article_detail_handler))
        self.assertTrue(callable(get_articles_handler))
        self.assertTrue(callable(get_recent_articles_handler))

    def test_statistics_module_exports_handler_and_payload_builders(self) -> None:
        from desktop_backend.statistics import (
            StatisticsPayload,
            build_statistics_payload,
            get_statistics_handler,
        )

        self.assertTrue(callable(get_statistics_handler))
        self.assertTrue(callable(build_statistics_payload))
        self.assertTrue(isinstance(StatisticsPayload, type))

    def test_query_handlers_re_exports_article_domain_handlers(self) -> None:
        import desktop_backend.articles.command_handlers as article_commands
        import desktop_backend.articles.query_handlers as article_queries
        import desktop_backend.query_handlers as query_handlers

        self.assertIs(
            query_handlers.MAX_ARTICLES_PAGE_SIZE,
            article_queries.MAX_ARTICLES_PAGE_SIZE,
        )
        self.assertIs(
            query_handlers.get_article_detail_handler,
            article_queries.get_article_detail_handler,
        )
        self.assertIs(
            query_handlers.get_articles_handler,
            article_queries.get_articles_handler,
        )
        self.assertIs(
            query_handlers.get_recent_articles_handler,
            article_queries.get_recent_articles_handler,
        )
        self.assertIs(
            query_handlers.delete_selected_articles_handler,
            article_commands.delete_selected_articles_handler,
        )
        self.assertIs(
            query_handlers.retry_empty_content_articles_handler,
            article_commands.retry_empty_content_articles_handler,
        )
        self.assertIs(
            query_handlers.retry_failed_articles_handler,
            article_commands.retry_failed_articles_handler,
        )

    def test_schemas_re_exports_article_payload_types_and_builders(self) -> None:
        import desktop_backend.articles.payloads as article_payloads
        import desktop_backend.schemas as schemas

        self.assertIs(
            schemas.ArticleDetailPayload,
            article_payloads.ArticleDetailPayload,
        )
        self.assertIs(schemas.ArticlePayload, article_payloads.ArticlePayload)
        self.assertIs(schemas.ArticlesPayload, article_payloads.ArticlesPayload)
        self.assertIs(
            schemas.RecentArticlePayload,
            article_payloads.RecentArticlePayload,
        )
        self.assertIs(
            schemas.build_article_detail_payload,
            article_payloads.build_article_detail_payload,
        )
        self.assertIs(
            schemas.build_article_payload,
            article_payloads.build_article_payload,
        )
        self.assertIs(
            schemas.build_articles_payload,
            article_payloads.build_articles_payload,
        )
        self.assertIs(
            schemas.build_recent_article_payload,
            article_payloads.build_recent_article_payload,
        )

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
