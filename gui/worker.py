"""
Background Worker Classes for GUI Operations
Provides thread-safe communication between background tasks and GUI
"""
import threading
import queue
import time
import pyautogui
import json
from pathlib import Path
from services.workflows import (
    generate_article_index,
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

    def emit_progress(self, current, total, message=""):
        """Emit a progress update"""
        self.signals.emit('progress', current=current, total=total, message=message)

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

    def run(self):
        """Run the content scraping process"""
        try:
            self.emit_status("初始化中...")
            result = run_scrape_workflow(
                db=Database(),
                scraper=ContentScraper(stop_checker=self.should_stop),
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

    def __init__(self, step_callback):
        super().__init__()
        self.step_callback = step_callback

    def run(self):
        """Run calibration in steps"""
        try:
            self.emit_status("校准中...")
            self.emit_log("开始坐标校准...")
            copy_link_countdown_seconds = 10
            open_tabs_clicks = 20
            cancelled = False

            def ask_pos(prompt: str):
                """Get a mouse position from UI; treat Cancel as a graceful abort."""
                nonlocal cancelled
                pos = self.step_callback(prompt)
                if pos is None:
                    cancelled = True
                    self.emit_log("用户取消校准")
                    self.emit_status("已取消")
                    self.emit_complete(cancelled=True)
                    return None
                return pos

            # Load or create config
            config_path = Path(__file__).parent.parent / "config" / "coordinates.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)

            if not config_path.exists():
                config = {
                    "windows": {
                        "article_list": {
                            "article_click_area": {"x": 0, "y": 0},
                            "row_height": 0,
                            "scroll_amount": 3,
                            "visible_articles": 5
                        },
                        "browser": {
                            "more_button": {"x": 0, "y": 0},
                            "copy_link_menu": {"x": 0, "y": 0},
                            "first_tab": {"x": 0, "y": 0},
                            "close_tab_button": {"x": 0, "y": 0}
                        }
                    },
                    "timing": {
                        "click_interval": 0.3,
                        "page_load_wait": 10.0,
                        "menu_open_wait": 0.5
                    },
                    "collection": {
                        "max_articles": 1000
                    }
                }
            else:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Step 1: Measure row height
            self.emit_progress(1, 8, "测量文章行高")
            pos1 = ask_pos("请将鼠标移动到【任意一篇文章的顶部】，点击记录后继续")
            if cancelled:
                return
            pos2 = ask_pos("请将鼠标移动到【下一篇文章的顶部】，点击记录后继续")
            if cancelled:
                return
            row_height = abs(pos2.y - pos1.y)
            self.emit_log(f"已计算行高: {row_height} 像素")

            # Step 2: Get article bottom
            self.emit_progress(2, 8, "获取文章底部位置")
            pos_bottom = ask_pos("请将鼠标移动到【第一篇文章的底部】，点击记录后继续")
            if cancelled:
                return
            click_y = pos_bottom.y - row_height // 2
            config['windows']['article_list']['article_click_area'] = {
                "x": pos_bottom.x, "y": click_y, "description": "文章点击位置（自动计算）"
            }
            config['windows']['article_list']['row_height'] = row_height

            # Step 3: Test scroll
            self.emit_progress(3, 8, "测试滚动单位")
            pos_before = ask_pos("将鼠标移动到文章列表区域内的参考点，点击记录后系统将自动滚动")
            if cancelled:
                return
            pyautogui.scroll(-1)
            time.sleep(1)
            pos_after = ask_pos("滚动完成后，将鼠标移动到同一参考点，点击记录")
            if cancelled:
                return
            pixels_per_unit = abs(pos_after.y - pos_before.y)
            scroll_amount = round(row_height / pixels_per_unit) if pixels_per_unit > 0 else 3
            config["windows"]["article_list"]["scroll_amount"] = scroll_amount
            self.emit_log(f"已记录滚动单位: {scroll_amount}")

            # Step 4: Visible articles
            self.emit_progress(4, 8, "设置可见文章数")
            visible_count = 5  # Default, can be configurable
            config['windows']['article_list']['visible_articles'] = visible_count

            # Step 5: More button
            self.emit_progress(5, 8, "定位更多按钮")
            more_btn = ask_pos("请将鼠标移动到【右上角更多按钮】上，点击记录")
            if cancelled:
                return
            config['windows']['browser']['more_button'] = {
                "x": more_btn.x, "y": more_btn.y, "description": "右上角更多按钮"
            }

            # Step 6: Copy link menu
            self.emit_progress(6, 8, "定位复制链接菜单")
            # WeChat's "more" menu steals focus; use a countdown to give time to open it and hover the item.
            start = ask_pos(
                "获取【复制链接菜单项】位置\n\n"
                f"确认(Enter)后，将开始 {copy_link_countdown_seconds} 秒倒计时。\n"
                "请在倒计时内完成：\n"
                "1) 点击右上角【更多】按钮打开菜单\n"
                "2) 将鼠标移动到【复制链接】菜单项上并保持不动\n\n"
                "倒计时结束后将自动记录当前鼠标位置。"
            )
            if cancelled:
                return

            for i in range(copy_link_countdown_seconds, 0, -1):
                # Emit as progress so the GUI can show it on the calibration page.
                self.emit_progress(6, 8, f"复制链接菜单倒计时: {i} 秒")
                time.sleep(1)

            copy_menu = pyautogui.position()
            config['windows']['browser']['copy_link_menu'] = {
                "x": copy_menu.x, "y": copy_menu.y, "description": "复制链接菜单项"
            }

            # Step 7: First tab
            self.emit_progress(7, 8, "定位第一个标签")
            click_area = config['windows']['article_list'].get('article_click_area') or {}
            click_x = click_area.get('x')
            click_y = click_area.get('y')
            if click_x is None or click_y is None:
                raise RuntimeError("文章点击位置未校准，无法自动打开标签")

            start = self.step_callback(
                f"标签管理准备\n\n"
                f"确认(Enter)后，程序将自动点击文章 {open_tabs_clicks} 次以提前打开标签。\n"
                "请确保微信窗口已就绪，且不要移动鼠标/窗口。\n\n"
                "提示：如需中止，可将鼠标移到屏幕角落触发 pyautogui failsafe。"
            )
            if start is None:
                self.emit_log("用户取消校准")
                self.emit_status("已取消")
                self.emit_complete(cancelled=True)
                return

            self.emit_log(f"开始自动点击文章 {open_tabs_clicks} 次以打开标签...")
            for i in range(open_tabs_clicks):
                pyautogui.click(click_x, click_y)
                self.emit_progress(7, 8, f"自动打开标签: {i + 1}/{open_tabs_clicks}")
                time.sleep(2)
            self.emit_log("已打开标签，准备记录第一个标签位置")

            first_tab = ask_pos("将鼠标移动到【第一个标签】上，确认(Enter)后记录位置")
            if cancelled:
                return
            config['windows']['browser']['first_tab'] = {
                "x": first_tab.x, "y": first_tab.y, "description": "第一个标签位置"
            }

            # Step 8: Close button
            self.emit_progress(8, 8, "定位关闭按钮")
            close_btn = ask_pos("请将鼠标移动到【标签关闭按钮】上，点击记录")
            if cancelled:
                return
            config['windows']['browser']['close_tab_button'] = {
                "x": close_btn.x, "y": close_btn.y, "description": "标签关闭按钮"
            }

            # Save config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.emit_log(f"坐标配置已保存到: {config_path}")
            self.emit_status("完成")
            self.emit_complete(path=str(config_path))

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"校准失败: {str(e)}")


class TestWorker(WorkerThread):
    """Worker for testing calibration in background thread"""

    def run(self):
        """Run the calibration test"""
        try:
            self.emit_status("初始化中...")

            import json
            import pyautogui
            from pathlib import Path

            config_path = Path(__file__).parent.parent / "config" / "coordinates.json"

            if not config_path.exists():
                self.emit_error("配置文件不存在，请先进行校准")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.emit_log("=== 开始测试坐标 ===\n")

            # Test 1: Article click position
            self.emit_log("--- 测试文章点击位置 ---")
            click_area = config['windows']['article_list']['article_click_area']
            self.emit_log(f"文章点击位置: ({click_area['x']}, {click_area['y']})")
            self.emit_log("请移动鼠标到该位置，确认是否在第一篇文章中间")
            self.emit_log("提示：鼠标将自动移动到该位置\n")

            pyautogui.moveTo(click_area['x'], click_area['y'], duration=1)

            # Test 2: Scroll amount
            self.emit_log("--- 测试滚动功能 ---")
            scroll_amount = config['windows']['article_list']['scroll_amount']
            self.emit_log(f"滚动距离: {scroll_amount} 像素")
            self.emit_log("确认后，程序将执行一次滚动")
            self.emit_log("请确认滚动距离是否正确\n")

            pyautogui.moveTo(click_area['x'], click_area['y'])
            pyautogui.scroll(-scroll_amount)

            # Test 3: More button
            self.emit_log("--- 测试更多按钮位置 ---")
            more_btn = config['windows']['browser']['more_button']
            self.emit_log(f"更多按钮位置: ({more_btn['x']}, {more_btn['y']})")
            self.emit_log("提示：鼠标将自动移动到该位置\n")

            pyautogui.moveTo(more_btn['x'], more_btn['y'], duration=1)

            # Test 4: Copy link menu
            self.emit_log("--- 测试复制链接菜单位置 ---")
            copy_menu = config['windows']['browser']['copy_link_menu']
            self.emit_log(f"复制链接菜单位置: ({copy_menu['x']}, {copy_menu['y']})")
            self.emit_log("操作：点击更多按钮后，鼠标将移动到复制链接菜单")
            self.emit_log("请确认位置是否正确\n")

            pyautogui.moveTo(more_btn['x'], more_btn['y'], duration=1)
            pyautogui.click()
            time.sleep(0.5)
            pyautogui.moveTo(copy_menu['x'], copy_menu['y'], duration=1)

            # Test 5: Tab close button
            self.emit_log("--- 测试标签关闭按钮位置 ---")
            first_tab = config['windows']['browser']['first_tab']
            close_btn = config['windows']['browser']['close_tab_button']
            self.emit_log(f"第一个标签位置: ({first_tab['x']}, {first_tab['y']})")
            self.emit_log(f"关闭按钮位置: ({close_btn['x']}, {close_btn['y']})")
            self.emit_log("提示：程序将点击第一个标签以激活，然后移动并点击关闭按钮\n")

            pyautogui.moveTo(first_tab['x'], first_tab['y'], duration=1)
            time.sleep(0.3)
            pyautogui.click()
            time.sleep(0.2)
            pyautogui.moveTo(close_btn['x'], close_btn['y'], duration=1)
            time.sleep(0.2)
            pyautogui.click()

            self.emit_log("\n=== 测试完成 ===")
            self.emit_status("完成")
            self.emit_complete(stopped=False)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"测试失败: {str(e)}")
