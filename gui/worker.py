"""
Background Worker Classes for GUI Operations
Provides thread-safe communication between background tasks and GUI
"""
import threading
import queue
import time
import pyautogui
from services.calibration_service import (
    run_calibration_flow,
    run_calibration_test_flow,
)
from services.workflows import (
    generate_article_index,
    reset_empty_content_articles,
    reset_failed_articles,
    run_collection_workflow,
    run_scrape_workflow,
)
from scraper.link_collector import LinkCollector
from scraper.content_scraper import ContentScraper
from storage.database import Database


class WorkerSignals:
    """Thread-safe signal queue for worker to GUI communication"""
    def __init__(self):
        self.queue = queue.Queue()

    def emit(self, signal_type, **kwargs):
        """Emit a signal to the GUI"""
        self.queue.put((signal_type, kwargs))

    def get(self, timeout=0.1):
        """Get a signal from the queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None


class WorkerThread(threading.Thread):
    """Base class for worker threads"""
    def __init__(self):
        super().__init__(daemon=True)
        self.signals = WorkerSignals()
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop"""
        self._stop_requested = True

    def should_stop(self):
        """Check if stop was requested"""
        return self._stop_requested

    def emit_log(self, message):
        """Emit a log message"""
        self.signals.emit('log', message=message)

    def emit_progress(self, current, total, message="", **kwargs):
        """Emit a progress update"""
        self.signals.emit('progress', current=current, total=total, message=message, **kwargs)

    def emit_status(self, status):
        """Emit a status update"""
        self.signals.emit('status', status=status)

    def emit_error(self, message):
        """Emit an error message"""
        self.signals.emit('error', message=message)

    def emit_complete(self, **kwargs):
        """Emit completion signal"""
        self.signals.emit('complete', **kwargs)


class LinkCollectorWorker(WorkerThread):
    """Worker for link collection in background thread"""

    def run(self):
        """Run the link collection process"""
        try:
            self.emit_status("初始化中...")

            collector = LinkCollector()
            collector.stop_checker = self.should_stop
            self.emit_status("采集中...")
            result = run_collection_workflow(
                collector,
                log=self.emit_log,
                progress=self.emit_progress,
            )

            if result.stopped:
                self.emit_status("已停止")
                time.sleep(0.05)
                self.emit_complete(stopped=True, count=result.count)
                return

            self.emit_status("完成")
            self.emit_complete(stopped=False, count=result.count)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"采集失败: {str(e)}")


class ContentScraperWorker(WorkerThread):
    """Worker for content scraping in background thread"""

    def __init__(self, pending_articles=None):
        super().__init__()
        self.pending_articles = pending_articles

    def run(self):
        """Run the content scraping process"""
        try:
            self.emit_status("初始化中...")
            result = run_scrape_workflow(
                db=Database(),
                scraper=ContentScraper(stop_checker=self.should_stop),
                pending_articles=self.pending_articles,
                log=self.emit_log,
                progress=self.emit_progress,
            )

            if result.total == 0 and not result.stopped:
                self.emit_status("无待处理")
                self.emit_complete(count=0, success=0, failed=0)
                return

            if result.stopped:
                self.emit_status("已停止")
                time.sleep(0.05)
                self.emit_complete(
                    stopped=True,
                    count=result.total,
                    success=result.success,
                    failed=result.failed,
                )
                return

            self.emit_status("完成")
            self.emit_complete(
                stopped=False,
                count=result.total,
                success=result.success,
                failed=result.failed,
            )

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"抓取失败: {str(e)}")


class RetryFailedWorker(WorkerThread):
    """Worker for retrying failed articles"""

    def run(self):
        """Reset failed articles to pending"""
        try:
            self.emit_status("处理中...")
            affected = reset_failed_articles(Database())

            if affected > 0:
                self.emit_log(f"已将 {affected} 篇失败文章重置为待抓取状态")
            else:
                self.emit_log("没有失败的文章需要重试")

            self.emit_status("完成")
            self.emit_complete(count=affected)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"操作失败: {str(e)}")


class RetryEmptyContentWorker(WorkerThread):
    """Worker for resetting empty-content articles"""

    def run(self):
        """Reset empty-content articles to pending"""
        try:
            self.emit_status("处理中...")
            affected = reset_empty_content_articles(Database())

            if affected > 0:
                self.emit_log(f"已将 {affected} 篇无内容文章重置为待抓取状态")
            else:
                self.emit_log("没有无内容文章需要重新抓取")

            self.emit_status("完成")
            self.emit_complete(count=affected)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"操作失败: {str(e)}")


class GenerateIndexWorker(WorkerThread):
    """Worker for generating article index"""

    def run(self):
        """Generate article index"""
        try:
            self.emit_status("生成中...")
            index_path = generate_article_index()
            self.emit_log(f"索引已生成: {index_path}")
            self.emit_status("完成")
            self.emit_complete(path=index_path)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"生成索引失败: {str(e)}")


class CalibrationWorker(WorkerThread):
    """Worker for coordinate calibration"""

    def __init__(self, step_callback, integer_callback=None):
        super().__init__()
        self.step_callback = step_callback
        self.integer_callback = integer_callback

    def run(self):
        """Run calibration in steps"""
        try:
            self.emit_status("校准中...")
            path = run_calibration_flow(
                mode="gui",
                ask_position=self.step_callback,
                ask_integer=(
                    self.integer_callback
                    if self.integer_callback is not None
                    else lambda prompt, default: default
                ),
                log=self.emit_log,
                progress=self.emit_progress,
                sleep=time.sleep,
                click=pyautogui.click,
                scroll=pyautogui.scroll,
                get_current_position=pyautogui.position,
            )

            if path is None:
                self.emit_log("用户取消校准")
                self.emit_status("已取消")
                self.emit_complete(cancelled=True)
                return

            self.emit_status("完成")
            self.emit_complete(path=str(path))

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"校准失败: {str(e)}")


class TestWorker(WorkerThread):
    """Worker for testing calibration in background thread"""

    def __init__(self, pause_callback, confirm_callback):
        super().__init__()
        self.pause_callback = pause_callback
        self.confirm_callback = confirm_callback

    def run(self):
        """Run the calibration test"""
        try:
            self.emit_status("初始化中...")
            result = run_calibration_test_flow(
                mode="gui",
                log=self.emit_log,
                move_to=pyautogui.moveTo,
                click=pyautogui.click,
                scroll=pyautogui.scroll,
                sleep=time.sleep,
                pause=self.pause_callback,
                confirm=self.confirm_callback,
            )

            if result is None:
                self.emit_status("已取消")
                self.emit_complete(cancelled=True)
                return

            if result is False:
                self.emit_status("未通过")
                self.emit_complete(passed=False)
                return

            self.emit_status("完成")
            self.emit_complete(stopped=False, passed=True)

        except FileNotFoundError:
            self.emit_status("错误")
            self.emit_error("配置文件不存在，请先进行校准")
        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"测试失败: {str(e)}")
