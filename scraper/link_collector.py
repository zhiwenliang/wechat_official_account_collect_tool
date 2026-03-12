"""
链接采集模块
通过pyautogui控制微信PC客户端，采集公众号文章链接
"""
import pyautogui
import pyperclip
import json
import platform
from pathlib import Path
from collections import deque
from services.calibration_service import load_required_coordinates_config
from services.workflows import run_collection_workflow
from storage.database import Database
from utils.stop_control import should_stop as stop_requested, sleep_with_stop

class LinkCollector:
    def __init__(self, config_path="config/coordinates.json"):
        self.config = self._load_config(config_path)
        self.collected_links = set()
        self.recent_links = deque(maxlen=5)
        self.is_macos = platform.system() == 'Darwin'
        self.db = Database()
        self.stop_checker = None
        pyautogui.FAILSAFE = True

    def _load_config(self, config_path):
        """加载坐标配置"""
        if config_path == "config/coordinates.json":
            return load_required_coordinates_config()

        path = Path(config_path)

        # 确保config目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {path}\n"
                f"请先运行: python main.py calibrate"
            )

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _click(self, x, y, description=""):
        """点击指定坐标"""
        if self.should_stop():
            return False
        if description:
            print(f"  点击: {description} ({x}, {y})")
        pyautogui.click(x, y)
        return self._sleep_with_stop(self.config['timing']['click_interval'])

    def _wait(self, wait_type='page_load'):
        """等待指定时间"""
        wait_time = self.config['timing'].get(f'{wait_type}_wait', 1.0)
        return self._sleep_with_stop(wait_time)

    def should_stop(self):
        """检查是否收到停止信号"""
        return stop_requested(self.stop_checker)

    def _sleep_with_stop(self, duration):
        """可响应停止信号的睡眠"""
        return sleep_with_stop(self.stop_checker, duration)

    def _activate_article_window(self):
        """激活公众号窗口"""
        if self.should_stop():
            return False

        # macOS需要点击来激活窗口，Windows不需要
        if self.is_macos:
            article_area = self.config['windows']['article_list']['article_click_area']
            pyautogui.click(article_area['x'], article_area['y'])
            return self._sleep_with_stop(0.2)

        return True

    def collect_link(self):
        """采集单篇文章链接"""
        max_retries = 3

        for attempt in range(max_retries):
            if self.should_stop():
                return None

            try:
                pyperclip.copy("")

                more_btn = self.config['windows']['browser']['more_button']
                if not self._click(more_btn['x'], more_btn['y'], "更多按钮"):
                    return None

                wait_time = self.config['timing']['menu_open_wait'] + attempt
                if not self._sleep_with_stop(wait_time):
                    return None

                copy_menu = self.config['windows']['browser']['copy_link_menu']
                if not self._click(copy_menu['x'], copy_menu['y'], "复制链接"):
                    return None
                if not self._sleep_with_stop(wait_time):
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

    def _check_duplicate_count(self):
        """检查最近链接的连续重复次数"""
        if len(self.recent_links) < 2:
            return 0

        last_link = self.recent_links[-1]
        count = 0
        for link in reversed(self.recent_links):
            if link == last_link:
                count += 1
            else:
                break
        return count

    def click_article(self, click_y):
        """点击文章"""
        if not self._activate_article_window():
            return False
        click_x = self.config['windows']['article_list']['article_click_area']['x']
        if not self._click(click_x, click_y, f"文章(y={click_y})"):
            return False
        return self._wait('page_load')

    def scroll_article(self):
        """滚动一个行高"""
        if self.should_stop():
            return False
        article_area = self.config['windows']['article_list']['article_click_area']
        pyautogui.moveTo(article_area['x'], article_area['y'])
        scroll_amount = self.config['windows']['article_list']['scroll_amount']
        pyautogui.scroll(-scroll_amount)
        return self._sleep_with_stop(2.0)

    def refresh_scroll(self):
        """向上再向下滚动相同单位，用于刷新页面加载"""
        if self.should_stop():
            return False
        article_area = self.config['windows']['article_list']['article_click_area']
        scroll_amount = self.config['windows']['article_list']['scroll_amount']

        print("  尝试刷新页面加载...")
        pyautogui.moveTo(article_area['x'], article_area['y'])

        # 向上滚动
        pyautogui.scroll(scroll_amount)
        if not self._sleep_with_stop(1.0):
            return False

        # 向下滚动相同单位
        pyautogui.scroll(-scroll_amount)
        if not self._sleep_with_stop(2.0):
            return False
        print("  ✓ 刷新完成")
        return True

    def close_tabs(self):
        """关闭多余的标签，只保留一个"""
        if self.should_stop():
            return False
        print("  开始关闭多余标签...")
        first_tab = self.config['windows']['browser']['first_tab']
        close_btn = self.config['windows']['browser']['close_tab_button']

        if not self._click(first_tab['x'], first_tab['y'], "第一个标签"):
            return False

        for i in range(19):
            if not self._click(close_btn['x'], close_btn['y'], ""):
                return False
            if not self._sleep_with_stop(0.2):
                return False

        print("  ✓ 标签已清理\n")
        return True

    def run(self):
        """运行采集流程"""
        from utils.escape_listener import EscapeListener

        esc_listener = EscapeListener()

        print("=== 微信公众号文章链接采集 ===\n")

        print("准备工作检查：")
        print("1. 窗口1：已打开公众号页面，并点击【文章分组】，滚动到页面最顶部")
        print("2. 窗口2：已打开微信内置浏览器")
        print("3. 两个窗口不重叠且都可见")
        print("4. 已完成坐标校准\n")

        input("确认以上准备完成，按回车开始采集...")

        self.stop_checker = esc_listener.is_triggered
        esc_enabled = esc_listener.start()

        stop_hint = "将鼠标移到屏幕角落可紧急停止"
        if esc_enabled:
            stop_hint += "，按 Esc 也可停止"
        print(f"\n提示: {stop_hint}\n")
        self._sleep_with_stop(2)

        try:
            return run_collection_workflow(self, log=print)
        finally:
            esc_listener.stop()
            self.stop_checker = None

if __name__ == "__main__":
    collector = LinkCollector()
    collector.run()
