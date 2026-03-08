"""
测试阶段2：内容抓取功能
"""
from scraper.content_scraper import ContentScraper
from storage.database import Database
from storage.file_store import FileStore

def test_scrape():
    """测试抓取单篇文章"""
    # 测试链接
    test_url = "https://mp.weixin.qq.com/s/Xf6jPd16Xqf2EGteq-ABbQ"

    print("=== 测试阶段2：内容抓取 ===\n")
    print(f"测试链接: {test_url}\n")

    # 初始化
    scraper = ContentScraper()
    file_store = FileStore()
    db = Database()

    try:
        # 启动浏览器
        print("1. 启动浏览器...")
        scraper.start()
        print("   [OK] 浏览器已启动\n")

        # 抓取文章
        print("2. 抓取文章内容...")
        article_data = scraper.scrape_article(test_url)

        if article_data:
            print("   [OK] 抓取成功\n")
            print("3. 文章信息:")
            print(f"   标题: {article_data['title']}")
            print(f"   发布时间: {article_data['publish_time']}")
            print(f"   内容长度: {len(article_data['content_html'])} 字符\n")

            # 保存到文件
            print("4. 保存到文件...")
            file_path = file_store.save_article(article_data)
            print(f"   [OK] 已保存: {file_path}\n")

            # 保存到数据库
            print("5. 保存到数据库...")
            if not db.url_exists(test_url):
                db.add_article(test_url)

            db.update_article(
                test_url,
                title=article_data['title'],
                publish_time=article_data['publish_time'],
                scraped_at=article_data['scraped_at'],
                file_path=file_path,
                status='scraped'
            )
            print("   [OK] 已保存到数据库\n")

            print("=" * 60)
            print("测试完成！所有功能正常")
        else:
            print("   [FAIL] 抓取失败\n")

    except Exception as e:
        print(f"   [ERROR] 错误: {e}\n")

    finally:
        # 关闭浏览器
        print("\n关闭浏览器...")
        scraper.stop()
        print("[OK] 测试结束")

if __name__ == "__main__":
    test_scrape()
