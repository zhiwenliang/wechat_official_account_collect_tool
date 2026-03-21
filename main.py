"""
主入口脚本
整合链接采集和内容抓取功能
"""

import sys
import threading
from utils.escape_listener import EscapeListener
from utils.runtime_env import configure_runtime_environment

configure_runtime_environment()

from scraper.link_collector import LinkCollector
from scraper.content_scraper import ContentScraper
from services.data_transfer import export_data_bundle, import_database_file
from services.workflows import (
    generate_article_index,
    reset_failed_articles,
    run_scrape_workflow,
)
from storage.database import Database


def scrape_content():
    """抓取文章内容"""
    stop_event = threading.Event()
    esc_listener = EscapeListener(on_escape=stop_event.set)

    print("=== 微信公众号文章内容抓取 ===\n")

    esc_enabled = esc_listener.start()
    if esc_enabled:
        print("提示: 抓取过程中按 Esc 可停止任务\n")

    try:
        result = run_scrape_workflow(
            db=Database(),
            scraper=ContentScraper(stop_checker=stop_event.is_set),
            log=print,
        )
    finally:
        esc_listener.stop()

    if result.total == 0 and not result.stopped:
        print("\n提示: 使用 'python main.py stats' 查看数据库状态")
        return

    if result.failed > 0 and not result.stopped:
        print(f"\n提示: 使用 'python main.py retry' 重新抓取失败的文章")


def generate_index():
    """生成文章目录索引"""
    index_path = generate_article_index()
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

    if stats["failed"] > 0:
        print(f"\n失败的文章链接:")
        for url in stats["failed_urls"]:
            print(f"  - {url}")
        print(f"\n提示: 使用 'python main.py retry' 重新抓取失败的文章")


def retry_failed():
    """重新抓取失败的文章"""
    affected = reset_failed_articles(Database())

    if affected > 0:
        print(f"✓ 已将 {affected} 篇失败文章重置为待抓取状态")
        print("现在可以运行 'python main.py scrape' 重新抓取")
    else:
        print("没有失败的文章需要重试")


def export_data_bundle_command(output_path):
    """导出数据库和文章备份为 zip 数据包"""
    result = export_data_bundle(output_path)
    print(f"数据包已导出: {result.archive_path}")
    print(f"  共打包 {result.file_count} 个文件")


def import_database_command(source_db_path):
    """导入外部数据库文件覆盖当前运行时数据库"""
    result = import_database_file(source_db_path)
    print(f"已导入数据库: {result.source_db_path}")
    print(f"  当前数据库位置: {result.target_db_path}")
    if result.backup_path:
        print(f"  已备份旧数据库: {result.backup_path}")
    print("提示: 本操作只替换数据库文件，不会同步 HTML/Markdown 备份目录")


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
        print("  python main.py export-data <zip_path> - 导出数据库和文章备份")
        print("  python main.py import-db <db_path>    - 导入外部数据库文件")
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
    elif command == "export-data":
        if len(sys.argv) < 3:
            print("用法: python main.py export-data <zip_path>")
            return
        try:
            export_data_bundle_command(sys.argv[2])
        except Exception as exc:
            print(f"导出失败: {exc}")
            raise SystemExit(1)
    elif command == "import-db":
        if len(sys.argv) < 3:
            print("用法: python main.py import-db <db_path>")
            return
        try:
            import_database_command(sys.argv[2])
        except Exception as exc:
            print(f"导入失败: {exc}")
            raise SystemExit(1)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
