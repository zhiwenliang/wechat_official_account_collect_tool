"""
内容抓取模块
使用Playwright访问文章链接，提取详细内容
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from pathlib import Path

class ContentScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

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
        try:
            self.page.goto(url, timeout=30000)
            time.sleep(3)

            # 等待内容加载
            self.page.wait_for_selector('#js_content', timeout=10000)

            # 提取标题
            title = self.page.locator('#activity-name').inner_text()

            # 提取发布时间
            publish_time_raw = self.page.locator('#publish_time').inner_text()
            publish_time = self._parse_publish_time(publish_time_raw)

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
            print(f"抓取失败: {url}, 错误: {e}")
            return None
