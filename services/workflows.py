"""
Shared task workflows used by both CLI and GUI.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from storage.database import Database
from storage.file_store import FileStore


LogFn = Callable[[str], None]
ProgressFn = Callable[..., None]


@dataclass
class CollectionResult:
    stopped: bool
    count: int
    start_time: datetime
    end_time: datetime


@dataclass
class ScrapeResult:
    stopped: bool
    success: int
    failed: int
    total: int
    start_time: datetime
    end_time: datetime
    index_path: Optional[str] = None


def _emit_progress(
    progress: Optional[ProgressFn],
    current: int,
    total: int,
    message: str = "",
    **kwargs,
):
    if progress:
        progress(current, total, message, **kwargs)


def _remaining_visible_article_click_positions(collector, remaining_count: int) -> list[int]:
    """Return click positions for the remaining visible rows on the last screen."""
    article_list = collector.config["windows"]["article_list"]
    base_y = article_list["article_click_area"]["y"]
    row_height = int(article_list.get("row_height") or 0)

    if row_height <= 0:
        return [base_y for _ in range(remaining_count)]

    return [base_y + (index * row_height) for index in range(remaining_count)]


def run_collection_workflow(collector, *, log: LogFn = print, progress: Optional[ProgressFn] = None):
    """Run the shared Stage 1 collection workflow."""
    start_time = datetime.now()

    log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log("准备采集链接...\n")

    current_click_y = collector.config['windows']['article_list']['article_click_area']['y']
    article_count = 0
    max_articles = collector.config['collection']['max_articles']
    has_refreshed = False
    consecutive_failures = 0
    max_consecutive_failures = 10
    stopped = False

    def save_link(link: str) -> bool:
        """Persist a collected link and report whether it is new."""
        if link in collector.collected_links:
            log("  重复链接，已跳过")
            return False

        collector.collected_links.add(link)
        added_id = collector.db.add_article(link)
        if added_id is None:
            log("  链接已存在于数据库，已跳过")
            return False

        return True

    log(f"开始采集 (最多{max_articles}篇)\n")

    while article_count < max_articles:
        if collector.should_stop():
            stopped = True
            break

        log(f"\n[{article_count + 1}] 处理中...")

        if not collector.click_article(current_click_y):
            stopped = collector.should_stop()
            if stopped:
                break

        link = collector.collect_link()

        if collector.should_stop():
            stopped = True
            break

        if link:
            collector.recent_links.append(link)
            consecutive_failures = 0

            duplicate_count = collector._check_duplicate_count()

            if duplicate_count >= 2 and duplicate_count < 5:
                log(f"  检测到连续{duplicate_count}次相同链接，继续滚动...")
            elif duplicate_count >= 5:
                if not has_refreshed:
                    log(f"\n检测到连续{duplicate_count}次相同链接，尝试刷新页面...")
                    if not collector.refresh_scroll():
                        stopped = collector.should_stop()
                        if stopped:
                            break
                    has_refreshed = True
                    collector.recent_links.clear()
                    continue
                else:
                    log(f"\n刷新后仍检测到连续{duplicate_count}次相同链接，确认已滚动到底")
                    break

            if save_link(link):
                article_count += 1
                log(f"  已保存: {link}")
                has_refreshed = False
                _emit_progress(progress, article_count, max_articles)

                if article_count % 30 == 0:
                    log(f"\n已采集{article_count}篇，清理标签...")
                    if not collector.close_tabs():
                        stopped = collector.should_stop()
                        if stopped:
                            break
        else:
            log("  未获取到有效链接")
            consecutive_failures += 1

            if consecutive_failures >= max_consecutive_failures:
                log(f"\n连续{consecutive_failures}次未获取到有效链接，停止采集")
                break

        if not collector.scroll_article():
            stopped = collector.should_stop()
            if stopped:
                break

    if not stopped and article_count < max_articles:
        remaining_count = collector.config['windows']['article_list']['visible_articles']
        log(f"\n处理剩余 {remaining_count} 篇可见文章（不滚动）\n")

        for i, click_y in enumerate(_remaining_visible_article_click_positions(collector, remaining_count)):
            if article_count >= max_articles or collector.should_stop():
                stopped = collector.should_stop()
                break

            log(f"\n[剩余{i+1}/{remaining_count}] 处理中...")

            if not collector.click_article(click_y):
                stopped = collector.should_stop()
                if stopped:
                    break

            link = collector.collect_link()
            if collector.should_stop():
                stopped = True
                break

            if link and save_link(link):
                article_count += 1
                log(f"  已保存: {link}")
                _emit_progress(progress, article_count, max_articles)

    end_time = datetime.now()
    elapsed = end_time - start_time

    log("\n" + "=" * 60)
    if stopped:
        log("收到停止信号，已停止采集")
    else:
        log(f"采集完成！共采集 {article_count} 篇文章")
    log(f"数据已保存到数据库: {collector.db.db_path}")
    log(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"总耗时: {elapsed.total_seconds():.1f} 秒 ({elapsed.total_seconds()/60:.1f} 分钟)")
    if not stopped:
        log("\n下一步: 运行 'python main.py scrape' 抓取文章内容")

    return CollectionResult(
        stopped=stopped,
        count=article_count,
        start_time=start_time,
        end_time=end_time,
    )


def run_scrape_workflow(
    *,
    db: Optional[Database] = None,
    file_store: Optional[FileStore] = None,
    scraper=None,
    pending_articles=None,
    log: LogFn = print,
    progress: Optional[ProgressFn] = None,
):
    """Run the shared Stage 2 scraping workflow."""
    db = db or Database()
    file_store = file_store or FileStore()

    if scraper is None:
        raise ValueError("scraper is required")

    pending = pending_articles if pending_articles is not None else db.get_pending_articles()
    start_time = datetime.now()

    log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"待抓取文章: {len(pending)} 篇\n")

    if not pending:
        log("没有待抓取的文章")
        return ScrapeResult(
            stopped=False,
            success=0,
            failed=0,
            total=0,
            start_time=start_time,
            end_time=start_time,
        )

    scraper.start()

    success_count = 0
    failed_count = 0
    stopped = False
    index_path = None

    try:
        for idx, (article_id, url) in enumerate(pending, 1):
            if scraper.should_stop():
                stopped = True
                break

            current_status = db.get_article_status(url)
            if current_status == 'scraped':
                log(f"[{idx}/{len(pending)}] 跳过: {url}")
                log("  数据库中已存在，且状态为已抓取")
                continue

            log(f"[{idx}/{len(pending)}] 抓取: {url}")

            article_data = scraper.scrape_article(url)

            if scraper.should_stop():
                stopped = True
                break

            if article_data:
                content_markdown = file_store.render_markdown(article_data)
                file_path = file_store.save_article(article_data, content_markdown=content_markdown)

                db.update_article(
                    url,
                    title=article_data['title'],
                    publish_time=article_data['publish_time'],
                    scraped_at=article_data['scraped_at'],
                    file_path=file_path,
                    content_html=article_data.get('content_html', ''),
                    content_markdown=content_markdown,
                    status='scraped',
                )
                log(f"  已保存: {file_path}")
                success_count += 1
            else:
                db.update_article(url, status='failed')
                log("  抓取失败")
                failed_count += 1

            _emit_progress(
                progress,
                idx,
                len(pending),
                message=f"已处理 {idx}/{len(pending)} 篇",
                success=success_count,
                failed=failed_count,
            )
    finally:
        scraper.stop()

    if not stopped:
        log("\n生成文章目录索引...")
        index_path = file_store.generate_index()
        log(f"索引已生成: {index_path}")

    end_time = datetime.now()
    elapsed = end_time - start_time

    log("\n" + "=" * 60)
    if stopped:
        log("收到停止信号，已停止抓取")
    else:
        log("抓取完成！")
    log(f"成功: {success_count} 篇")
    log(f"失败: {failed_count} 篇")
    log(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"总耗时: {elapsed.total_seconds():.1f} 秒 ({elapsed.total_seconds()/60:.1f} 分钟)")

    return ScrapeResult(
        stopped=stopped,
        success=success_count,
        failed=failed_count,
        total=success_count + failed_count,
        start_time=start_time,
        end_time=end_time,
        index_path=index_path,
    )


def reset_failed_articles(db: Optional[Database] = None):
    """Reset failed article status to pending."""
    db = db or Database()
    return db.reset_failed()


def reset_empty_content_articles(db: Optional[Database] = None):
    """Reset scraped-but-empty articles to pending."""
    db = db or Database()
    return db.reset_empty_content()


def generate_article_index(file_store: Optional[FileStore] = None):
    """Generate the markdown index file."""
    file_store = file_store or FileStore()
    return file_store.generate_index()
