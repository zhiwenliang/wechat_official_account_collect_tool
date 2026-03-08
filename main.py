"""
主入口脚本
整合链接采集和内容抓取功能
"""
import sys
from pathlib import Path
from scraper.link_collector import LinkCollector
from scraper.content_scraper import ContentScraper
from storage.database import Database
from storage.file_store import FileStore

def import_links_to_db():
    """将links.txt中的链接导入数据库"""
    db = Database()
    links_file = Path("data/links.txt")

    if not links_file.exists():
        print("未找到 data/links.txt 文件")
        return

    with open(links_file, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    added = 0
    for link in links:
        if db.add_article(link):
            added += 1

    print(f"导入完成：共 {len(links)} 条链接，新增 {added} 条")

def scrape_content():
    """抓取文章内容"""
    db = Database()
    file_store = FileStore()
    scraper = ContentScraper()

    pending = db.get_pending_articles()
    print(f"待抓取文章: {len(pending)} 篇\n")

    if not pending:
        print("没有待抓取的文章")
        return

    scraper.start()

    try:
        for idx, (article_id, url) in enumerate(pending, 1):
            print(f"[{idx}/{len(pending)}] 抓取: {url}")

            article_data = scraper.scrape_article(url)

            if article_data:
                file_path = file_store.save_article(article_data)

                db.update_article(
                    url,
                    title=article_data['title'],
                    publish_time=article_data['publish_time'],
                    read_count=article_data['read_count'],
                    like_count=article_data['like_count'],
                    scraped_at=article_data['scraped_at'],
                    file_path=file_path,
                    status='scraped'
                )
                print(f"  ✓ 已保存: {file_path}")
            else:
                db.update_article(url, status='failed')
                print(f"  ✗ 抓取失败")

    finally:
        scraper.stop()

    print("\n抓取完成！")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python main.py calibrate  - 校准坐标")
        print("  python main.py test       - 测试校准结果")
        print("  python main.py collect    - 采集链接")
        print("  python main.py import     - 导入链接到数据库")
        print("  python main.py scrape     - 抓取文章内容")
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
    elif command == "import":
        import_links_to_db()
    elif command == "scrape":
        scrape_content()
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()
