"""
主入口脚本
整合链接采集和内容抓取功能
"""
import sys
from scraper.link_collector import LinkCollector
from scraper.content_scraper import ContentScraper
from storage.database import Database
from storage.file_store import FileStore
from markdownify import markdownify as md

def scrape_content():
    """抓取文章内容"""
    from datetime import datetime
    start_time = datetime.now()

    db = Database()
    file_store = FileStore()
    scraper = ContentScraper()

    pending = db.get_pending_articles()

    print("=== 微信公众号文章内容抓取 ===\n")
    print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"待抓取文章: {len(pending)} 篇\n")

    if not pending:
        print("没有待抓取的文章")
        print("\n提示: 使用 'python main.py stats' 查看数据库状态")
        return

    scraper.start()

    success_count = 0
    failed_count = 0

    try:
        for idx, (article_id, url) in enumerate(pending, 1):
            print(f"[{idx}/{len(pending)}] 抓取: {url}")

            article_data = scraper.scrape_article(url)

            if article_data:
                # 生成 Markdown
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
                print(f"  ✓ 已保存: {file_path}")
                success_count += 1
            else:
                db.update_article(url, status='failed')
                print(f"  ✗ 抓取失败")
                failed_count += 1

    finally:
        scraper.stop()

    # 生成文章目录索引
    print("\n生成文章目录索引...")
    index_path = file_store.generate_index()
    print(f"✓ 索引已生成: {index_path}")

    end_time = datetime.now()
    elapsed = end_time - start_time

    print("\n" + "=" * 60)
    print("抓取完成！")
    print(f"\n成功: {success_count} 篇")
    print(f"失败: {failed_count} 篇")
    print(f"\n开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {elapsed.total_seconds():.1f} 秒 ({elapsed.total_seconds()/60:.1f} 分钟)")

    if failed_count > 0:
        print(f"\n提示: 使用 'python main.py retry' 重新抓取失败的文章")

def generate_index():
    """生成文章目录索引"""
    file_store = FileStore()
    index_path = file_store.generate_index()
    print(f"✓ 索引已生成: {index_path}")

def show_statistics():
    """显示数据库统计信息"""
    db = Database()
    stats = db.get_statistics()

    print("=== 数据库统计信息 ===\n")
    print(f"总文章数: {stats['total']}")
    print(f"  - 待抓取: {stats['pending']}")
    print(f"  - 已抓取: {stats['scraped']}")
    print(f"  - 抓取失败: {stats['failed']}")

    if stats['failed'] > 0:
        print(f"\n失败的文章链接:")
        for url in stats['failed_urls']:
            print(f"  - {url}")
        print(f"\n提示: 使用 'python main.py retry' 重新抓取失败的文章")

def retry_failed():
    """重新抓取失败的文章"""
    db = Database()
    affected = db.reset_failed()

    if affected > 0:
        print(f"✓ 已将 {affected} 篇失败文章重置为待抓取状态")
        print("现在可以运行 'python main.py scrape' 重新抓取")
    else:
        print("没有失败的文章需要重试")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python main.py calibrate  - 校准坐标")
        print("  python main.py test       - 测试校准结果")
        print("  python main.py collect    - 采集链接（直接存入数据库）")
        print("  python main.py scrape     - 抓取文章内容")
        print("  python main.py index      - 生成文章目录索引")
        print("  python main.py stats      - 显示数据库统计信息")
        print("  python main.py retry      - 重新抓取失败的文章")
        return

    command = sys.argv[1]

    if command == "calibrate":
        from scraper.calibrator import calibrate
        calibrate()
    elif command == "test":
        from scraper.calibrator import test_calibration
        test_calibration()
    elif command == "collect":
        collector = LinkCollector()
        collector.run()
    elif command == "scrape":
        scrape_content()
    elif command == "index":
        generate_index()
    elif command == "stats":
        show_statistics()
    elif command == "retry":
        retry_failed()
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()
