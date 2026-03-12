"""
内容抓取模块
使用Playwright访问文章链接，提取详细内容
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
from datetime import datetime
from pathlib import Path
from utils.stop_control import should_stop as stop_requested, sleep_with_stop

class ContentScraper:
    def __init__(self, max_retries=3, retry_delay=10, stop_checker=None):
        self.playwright = None
        self.browser = None
        self.page = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stop_checker = stop_checker

    def should_stop(self):
        """检查是否收到停止信号"""
        return stop_requested(self.stop_checker)

    def _sleep_with_stop(self, duration):
        """可响应停止信号的睡眠"""
        return sleep_with_stop(self.stop_checker, duration)

    def _parse_publish_time(self, time_str):
        """解析发布时间，支持中文格式"""
        try:
            # 处理中文格式：2026年3月5日 23:39
            match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})', time_str)
            if match:
                year, month, day, hour, minute = match.groups()
                dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                return dt.isoformat()

            # 如果已经是ISO格式，直接返回
            return time_str
        except Exception as e:
            print(f"  警告: 时间解析失败: {time_str}, 错误: {e}")
            return time_str

    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()

    def stop(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_article(self, url):
        """抓取单篇文章"""
        for attempt in range(self.max_retries):
            if self.should_stop():
                return None

            try:
                self.page.goto(url, timeout=30000)
                if not self._sleep_with_stop(3):
                    return None

                # 等待内容加载
                self.page.wait_for_selector('#js_content', timeout=10000)
                if self.should_stop():
                    return None

                # 提取标题
                title = self.page.locator('#activity-name').inner_text()

                # 提取发布时间
                publish_time_raw = self.page.locator('#publish_time').inner_text()
                publish_time = self._parse_publish_time(publish_time_raw)

                # 滚动页面加载所有图片
                self._scroll_to_load_images()

                # 提取正文HTML
                content_html = self.page.locator('#js_content').inner_html()

                return {
                    'title': title.strip(),
                    'url': url,
                    'publish_time': publish_time,
                    'content_html': content_html,
                    'scraped_at': datetime.now().isoformat()
                }

            except Exception as e:
                if self.should_stop():
                    return None
                if attempt < self.max_retries - 1:
                    print(f"  抓取失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    print(f"  等待{self.retry_delay}秒后重试...")
                    if not self._sleep_with_stop(self.retry_delay):
                        return None
                else:
                    print(f"  抓取失败 (已重试{self.max_retries}次): {e}")
                    return None

        return None

    def _scroll_to_load_images(self):
        """滚动页面以加载所有图片"""
        try:
            if self.should_stop():
                return

            # 获取页面总高度
            total_height = self.page.evaluate("document.body.scrollHeight")
            viewport_height = self.page.evaluate("window.innerHeight")

            # 计算需要滚动的次数
            scroll_steps = int(total_height / viewport_height) + 1

            print(f"  正在滚动加载图片（共{scroll_steps}步）...")

            # 逐步滚动到底部
            for i in range(scroll_steps):
                if self.should_stop():
                    return
                scroll_position = viewport_height * i
                self.page.evaluate(f"window.scrollTo(0, {scroll_position})")
                if not self._sleep_with_stop(0.5):
                    return

            # 滚动到底部
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            if not self._sleep_with_stop(1):
                return

            # 滚回顶部
            self.page.evaluate("window.scrollTo(0, 0)")
            self._sleep_with_stop(0.5)

            print(f"  [OK] 图片加载完成")

        except Exception as e:
            print(f"  警告: 滚动加载图片时出错: {e}")
