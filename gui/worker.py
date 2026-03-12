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
from scraper.link_collector import LinkCollector
from scraper.content_scraper import ContentScraper
from storage.database import Database
from storage.file_store import FileStore
from markdownify import markdownify as md
from datetime import datetime


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
        stopped = False  # Single flag to track if we stopped

        try:
            self.emit_status("初始化中...")

            collector = LinkCollector()
            start_time = datetime.now()

            self.emit_log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log("准备采集链接...\n")

            # Share stop flag with collector
            collector.stop_requested = self._stop_requested

            # Override collect_link to check stop flag frequently
            def collect_link_with_stop():
                if self.should_stop():
                    return None

                import pyperclip
                max_retries = 3

                for attempt in range(max_retries):
                    if self.should_stop():
                        return None

                    try:
                        pyperclip.copy("")

                        more_btn = collector.config['windows']['browser']['more_button']
                        collector._click(more_btn['x'], more_btn['y'], "更多按钮")

                        wait_time = collector.config['timing']['menu_open_wait'] + attempt
                        time.sleep(wait_time)

                        # Check stop after sleep
                        if self.should_stop():
                            return None

                        copy_menu = collector.config['windows']['browser']['copy_link_menu']
                        collector._click(copy_menu['x'], copy_menu['y'], "复制链接")
                        time.sleep(wait_time)

                        # Check stop after sleep
                        if self.should_stop():
                            return None

                        link = pyperclip.paste().strip()

                        if link and link.startswith('http'):
                            if attempt > 0:
                                print(f"  ✓ 重试成功（第{attempt + 1}次尝试）")
                            return link
                        else:
                            if attempt < max_retries - 1:
                                print(f"  ⚠ 未获取到有效链接，{attempt + 1}秒后重试...")
                            else:
                                print(f"  ✗ 重试{max_retries}次后仍未获取到有效链接")

                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"  ⚠ 采集失败: {e}，{attempt + 1}秒后重试...")
                        else:
                            print(f"  ✗ 重试{max_retries}次后仍失败: {e}")

                return None

            # Keep both names to avoid mismatches in older code paths.
            collector.collect_link = collect_link_with_stop
            collector.collect_link_with_stop = collect_link_with_stop

            # Initialize
            current_click_y = collector.config['windows']['article_list']['article_click_area']['y']
            article_count = 0
            max_articles = collector.config['collection']['max_articles']
            has_refreshed = False
            consecutive_failures = 0
            max_consecutive_failures = 10

            self.emit_log(f"开始采集 (最多{max_articles}篇)\n")
            self.emit_status("采集中...")

            # Main collection loop
            while article_count < max_articles and not self.should_stop():
                self.emit_log(f"\n[{article_count + 1}] 处理中...")

                collector.click_article(current_click_y)

                # Check stop after click
                if self.should_stop():
                    stopped = True
                    break

                link = collector.collect_link_with_stop()

                if link:
                    collector.recent_links.append(link)
                    consecutive_failures = 0

                    # Check for duplicates
                    duplicate_count = collector._check_duplicate_count()

                    if duplicate_count >= 2 and duplicate_count < 5:
                        self.emit_log(f"  检测到连续{duplicate_count}次相同链接，继续滚动...")
                    elif duplicate_count >= 5:
                        if not has_refreshed:
                            self.emit_log(f"\n检测到连续{duplicate_count}次相同链接，尝试刷新页面...")
                            collector.refresh_scroll()
                            has_refreshed = True
                            collector.recent_links.clear()
                            continue
                        else:
                            self.emit_log(f"\n刷新后仍检测到连续{duplicate_count}次相同链接，确认已滚动到底")
                            break

                    if link not in collector.collected_links:
                        collector.collected_links.add(link)
                        collector.db.add_article(link)
                        article_count += 1
                        self.emit_log(f"  已保存: {link}")
                        has_refreshed = False

                        # Update progress
                        self.emit_progress(article_count, max_articles)

                        # Close tabs every 30 articles
                        if article_count % 30 == 0:
                            self.emit_log(f"\n已采集{article_count}篇，清理标签...")
                            collector.close_tabs()
                    else:
                        self.emit_log(f"  重复链接，已跳过")
                else:
                    self.emit_log(f"  未获取到有效链接")
                    consecutive_failures += 1

                    if consecutive_failures >= max_consecutive_failures:
                        self.emit_log(f"\n连续{consecutive_failures}次未获取到有效链接，停止采集")
                        break

                # Check stop before scroll
                if self.should_stop():
                    stopped = True
                    break

                collector.scroll_article()

            # If stopped, emit complete immediately and return
            if stopped:
                self.emit_log("\n收到停止信号，正在停止...")
                self.emit_status("已停止")
                # Small delay to ensure GUI receives the log before complete
                time.sleep(0.05)
                self.emit_complete(stopped=True, count=article_count)
                return

            # Process remaining visible articles (only if not stopped)
            if article_count < max_articles and not self.should_stop():
                remaining_count = collector.config['windows']['article_list']['visible_articles']
                self.emit_log(f"\n处理剩余 {remaining_count} 篇可见文章（不滚动）\n")

                for i in range(remaining_count):
                    if self.should_stop() or article_count >= max_articles:
                        stopped = True
                        break

                    self.emit_log(f"\n[剩余{i+1}/{remaining_count}] 处理中...")

                    collector.click_article(current_click_y)
                    link = collector.collect_link_with_stop()

                    if link and link not in collector.collected_links:
                        collector.collected_links.add(link)
                        collector.db.add_article(link)
                        article_count += 1
                        self.emit_log(f"  已保存: {link}")
                        self.emit_progress(article_count, max_articles)

            # If stopped during remaining processing, emit complete immediately
            if stopped:
                self.emit_log("\n收到停止信号，正在停止...")
                self.emit_status("已停止")
                time.sleep(0.05)
                self.emit_complete(stopped=True, count=article_count)
                return

            # Normal completion
            end_time = datetime.now()
            elapsed = end_time - start_time

            self.emit_log("\n" + "=" * 60)
            self.emit_log(f"采集完成！共采集 {article_count} 篇文章")
            self.emit_log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log(f"总耗时: {elapsed.total_seconds():.1f} 秒")

            self.emit_status("完成")
            self.emit_complete(stopped=False, count=article_count)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"采集失败: {str(e)}")


class ContentScraperWorker(WorkerThread):
    """Worker for content scraping in background thread"""

    def run(self):
        """Run the content scraping process"""
        stopped = False  # Single flag to track if we stopped

        try:
            self.emit_status("初始化中...")

            db = Database()
            file_store = FileStore()
            scraper = ContentScraper()

            pending = db.get_pending_articles()

            start_time = datetime.now()
            self.emit_log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log(f"待抓取文章: {len(pending)} 篇\n")

            if not pending:
                self.emit_log("没有待抓取的文章")
                self.emit_status("无待处理")
                self.emit_complete(count=0, success=0, failed=0)
                return

            scraper.start()

            success_count = 0
            failed_count = 0

            try:
                for idx, (article_id, url) in enumerate(pending, 1):
                    if self.should_stop():
                        stopped = True
                        break

                    self.emit_log(f"[{idx}/{len(pending)}] 抓取: {url}")
                    self.emit_progress(idx, len(pending))

                    article_data = scraper.scrape_article(url)

                    if article_data:
                        content_markdown = md(article_data.get('content_html', ''), heading_style="ATX")

                        file_path = file_store.save_article(article_data)

                        db.update_article(
                            url,
                            title=article_data['title'],
                            publish_time=article_data['publish_time'],
                            scraped_at=article_data['scraped_at'],
                            file_path=file_path,
                            content_html=article_data.get('content_html', ''),
                            content_markdown=content_markdown,
                            status='scraped'
                        )
                        self.emit_log(f"  已保存: {file_path}")
                        success_count += 1
                    else:
                        db.update_article(url, status='failed')
                        self.emit_log(f"  抓取失败")
                        failed_count += 1

            finally:
                scraper.stop()

            # If stopped, emit complete immediately and return
            if stopped:
                self.emit_log("\n收到停止信号，正在停止...")
                self.emit_status("已停止")
                time.sleep(0.05)
                self.emit_complete(stopped=True, count=success_count + failed_count, success=success_count, failed=failed_count)
                return

            # Generate index (only if not stopped)
            if not self.should_stop():
                self.emit_log("\n生成文章目录索引...")
                index_path = file_store.generate_index()
                self.emit_log(f"索引已生成: {index_path}")

            # Normal completion
            end_time = datetime.now()
            elapsed = end_time - start_time

            self.emit_log("\n" + "=" * 60)
            self.emit_log("抓取完成！")
            self.emit_log(f"成功: {success_count} 篇")
            self.emit_log(f"失败: {failed_count} 篇")
            self.emit_log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.emit_log(f"总耗时: {elapsed.total_seconds():.1f} 秒")

            self.emit_status("完成")
            self.emit_complete(stopped=False, count=success_count + failed_count, success=success_count, failed=failed_count)

        except Exception as e:
            self.emit_status("错误")
            self.emit_error(f"抓取失败: {str(e)}")


class RetryFailedWorker(WorkerThread):
    """Worker for retrying failed articles"""

    def run(self):
        """Reset failed articles to pending"""
        try:
            self.emit_status("处理中...")
            db = Database()
            affected = db.reset_failed()

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
            file_store = FileStore()
            index_path = file_store.generate_index()
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
