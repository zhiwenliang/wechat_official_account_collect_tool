"""
内容抓取模块
使用Playwright访问文章链接，提取详细内容
"""
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
from datetime import datetime
from pathlib import Path

class ContentScraper:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

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
            time.sleep(2)

            # 等待内容加载
            self.page.wait_for_selector('#js_content', timeout=10000)

            # 提取标题
            title = self.page.locator('#activity-name').inner_text()

            # 提取发布时间
            publish_time = self.page.locator('#publish_time').inner_text()

            # 提取阅读量（可能需要等待）
            read_count = None
            try:
                self.page.wait_for_selector('#js_read_count', timeout=5000)
                read_count = self.page.locator('#js_read_count').inner_text()
                read_count = int(read_count) if read_count.isdigit() else None
            except:
                pass

            # 提取点赞数
            like_count = None
            try:
                like_count = self.page.locator('#js_like_count').inner_text()
                like_count = int(like_count) if like_count.isdigit() else None
            except:
                pass

            # 提取正文HTML
            content_html = self.page.locator('#js_content').inner_html()

            return {
                'title': title.strip(),
                'url': url,
                'publish_time': publish_time.strip(),
                'read_count': read_count,
                'like_count': like_count,
                'content_html': content_html,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"抓取失败: {url}, 错误: {e}")
            return None
