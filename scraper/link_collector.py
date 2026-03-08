"""
链接采集模块
通过pyautogui控制微信PC客户端，采集公众号文章链接
"""
import pyautogui
import pyperclip
import time
import json
import platform
from pathlib import Path
from collections import deque

class LinkCollector:
    def __init__(self, config_path="config/coordinates.json"):
        self.config = self._load_config(config_path)
        self.collected_links = set()
        self.recent_links = deque(maxlen=5)
        self.is_macos = platform.system() == 'Darwin'
        pyautogui.FAILSAFE = True

    def _load_config(self, config_path):
        """加载坐标配置"""
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
        if description:
            print(f"  点击: {description} ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(self.config['timing']['click_interval'])

    def _wait(self, wait_type='page_load'):
        """等待指定时间"""
        wait_time = self.config['timing'].get(f'{wait_type}_wait', 1.0)
        time.sleep(wait_time)

    def _activate_article_window(self):
        """激活公众号窗口"""
        # macOS需要点击来激活窗口，Windows不需要
        if self.is_macos:
            article_area = self.config['windows']['article_list']['article_click_area']
            pyautogui.click(article_area['x'], article_area['y'])
            time.sleep(0.2)

    def collect_link(self):
        """采集单篇文章链接"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                pyperclip.copy("")

                more_btn = self.config['windows']['browser']['more_button']
                self._click(more_btn['x'], more_btn['y'], "更多按钮")

                wait_time = self.config['timing']['menu_open_wait'] + attempt
                time.sleep(wait_time)

                copy_menu = self.config['windows']['browser']['copy_link_menu']
                self._click(copy_menu['x'], copy_menu['y'], "复制链接")
                time.sleep(wait_time)

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
        self._activate_article_window()
        click_x = self.config['windows']['article_list']['article_click_area']['x']
        self._click(click_x, click_y, f"文章(y={click_y})")
        self._wait('page_load')

    def scroll_article(self):
        """滚动一个行高"""
        article_area = self.config['windows']['article_list']['article_click_area']
        pyautogui.moveTo(article_area['x'], article_area['y'])
        scroll_amount = self.config['windows']['article_list']['scroll_amount']
        pyautogui.scroll(-scroll_amount)
        time.sleep(2.0)

    def refresh_scroll(self):
        """向上再向下滚动相同单位，用于刷新页面加载"""
        article_area = self.config['windows']['article_list']['article_click_area']
        scroll_amount = self.config['windows']['article_list']['scroll_amount']

        print("  尝试刷新页面加载...")
        pyautogui.moveTo(article_area['x'], article_area['y'])

        # 向上滚动
        pyautogui.scroll(scroll_amount)
        time.sleep(1.0)

        # 向下滚动相同单位
        pyautogui.scroll(-scroll_amount)
        time.sleep(2.0)
        print("  ✓ 刷新完成")

    def close_tabs(self):
        """关闭多余的标签，只保留一个"""
        print("  开始关闭多余标签...")
        first_tab = self.config['windows']['browser']['first_tab']
        close_btn = self.config['windows']['browser']['close_tab_button']

        self._click(first_tab['x'], first_tab['y'], "第一个标签")

        for i in range(19):
            self._click(close_btn['x'], close_btn['y'], "")
            time.sleep(0.2)

        print("  ✓ 标签已清理\n")

    def run(self, output_file="data/links.txt"):
        """运行采集流程"""
        from datetime import datetime
        start_time = datetime.now()

        print("=== 微信公众号文章链接采集 ===\n")
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        print("准备工作检查：")
        print("1. 窗口1：已打开公众号页面，并点击【文章分组】，滚动到页面最顶部")
        print("2. 窗口2：已打开微信内置浏览器")
        print("3. 两个窗口不重叠且都可见")
        print("4. 已完成坐标校准\n")

        input("确认以上准备完成，按回车开始采集...")

        print("\n提示: 将鼠标移到屏幕角落可紧急停止\n")
        time.sleep(2)

        # 初始化点击位置（第一篇文章中间）
        current_click_y = self.config['windows']['article_list']['article_click_area']['y']

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        article_count = 0
        max_articles = self.config['collection']['max_articles']
        has_refreshed = False  # 标记是否已经尝试过刷新
        consecutive_failures = 0  # 连续失败次数
        max_consecutive_failures = 10  # 最大连续失败次数

        print(f"开始采集 (最多{max_articles}篇)\n")
        print("-" * 60)

        # 主循环：点击 -> 采集 -> 滚动
        while article_count < max_articles:
            print(f"\n[{article_count + 1}] 处理中...")

            self.click_article(current_click_y)
            link = self.collect_link()

            if link:
                self.recent_links.append(link)
                consecutive_failures = 0  # 重置失败计数

                duplicate_count = self._check_duplicate_count()

                if duplicate_count >= 2 and duplicate_count < 5:
                    print(f"  ⚠ 检测到连续{duplicate_count}次相同链接，继续滚动...")
                elif duplicate_count >= 5:
                    if not has_refreshed:
                        # 第一次检测到5次重复，尝试刷新
                        print(f"\n检测到连续{duplicate_count}次相同链接，尝试刷新页面...")
                        self.refresh_scroll()
                        has_refreshed = True
                        # 清空最近链接记录，重新开始计数
                        self.recent_links.clear()
                        continue
                    else:
                        # 刷新后仍然5次重复，确认到底
                        print(f"\n刷新后仍检测到连续{duplicate_count}次相同链接，确认已滚动到底")
                        break

                if link not in self.collected_links:
                    self.collected_links.add(link)

                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write(link + '\n')

                    article_count += 1
                    print(f"  ✓ 已保存: {link}")

                    # 重置刷新标志（有新链接说明还没到底）
                    has_refreshed = False

                    # 每30篇关闭多余标签
                    if article_count % 30 == 0:
                        print(f"\n已采集{article_count}篇，清理标签...")
                        self.close_tabs()
                else:
                    print(f"  ⚠ 重复链接，已跳过")
            else:
                print(f"  ✗ 未获取到有效链接")
                consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    print(f"\n连续{consecutive_failures}次未获取到有效链接，可能出现异常，停止采集")
                    break

            # 滚动到下一篇
            self.scroll_article()

        # 处理剩余文章
        if article_count < max_articles:
            print("\n" + "=" * 60)
            remaining_count = self.config['windows']['article_list']['visible_articles']
            print(f"处理剩余 {remaining_count} 篇可见文章（不滚动）\n")
                
            for i in range(remaining_count):
                if article_count >= max_articles:
                    break
                
                print(f"\n[剩余{i+1}/{remaining_count}] 处理中...")
                
                self.click_article(current_click_y)
                link = self.collect_link()

                if link and link not in self.collected_links:
                    self.collected_links.add(link)

                    with open(output_path, 'a', encoding='utf-8') as f:
                        f.write(link + '\n')

                    article_count += 1
                    print(f"  ✓ 已保存: {link}")

        print("\n" + "=" * 60)
        end_time = datetime.now()
        elapsed = end_time - start_time

        print(f"采集完成！共采集 {article_count} 篇文章")
        print(f"保存位置: {output_path.absolute()}")
        print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {elapsed.total_seconds():.1f} 秒 ({elapsed.total_seconds()/60:.1f} 分钟)")

if __name__ == "__main__":
    collector = LinkCollector()
    collector.run()
