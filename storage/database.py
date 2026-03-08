"""
数据库操作模块
使用SQLite存储文章信息
"""
import sqlite3
from pathlib import Path
from datetime import datetime

class Database:
    def __init__(self, db_path="data/articles.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT UNIQUE NOT NULL,
                publish_time TEXT,
                scraped_at TEXT,
                status TEXT DEFAULT 'pending',
                file_path TEXT
            )
        """)

        conn.commit()
        conn.close()

    def add_article(self, url, status='pending'):
        """添加文章链接"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO articles (url, status) VALUES (?, ?)",
                (url, status)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def update_article(self, url, **kwargs):
        """更新文章信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [url]

        cursor.execute(f"UPDATE articles SET {fields} WHERE url = ?", values)
        conn.commit()
        conn.close()

    def get_pending_articles(self):
        """获取待抓取的文章"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, url FROM articles WHERE status = 'pending'")
        articles = cursor.fetchall()
        conn.close()

        return articles

    def url_exists(self, url):
        """检查URL是否已存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        exists = cursor.fetchone() is not None
        conn.close()

        return exists

    def get_statistics(self):
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总数统计
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]

        # 按状态统计
        cursor.execute("SELECT status, COUNT(*) FROM articles GROUP BY status")
        status_counts = dict(cursor.fetchall())

        # 获取失败的文章
        cursor.execute("SELECT url FROM articles WHERE status = 'failed'")
        failed_urls = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            'total': total,
            'pending': status_counts.get('pending', 0),
            'scraped': status_counts.get('scraped', 0),
            'failed': status_counts.get('failed', 0),
            'failed_urls': failed_urls
        }

    def reset_failed(self):
        """重置失败的文章状态为pending"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("UPDATE articles SET status = 'pending' WHERE status = 'failed'")
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    def get_articles_by_status(self, status):
        """获取指定状态的文章列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, url, title, publish_time, scraped_at, file_path
            FROM articles
            WHERE status = ?
            ORDER BY id
        """, (status,))
        articles = cursor.fetchall()
        conn.close()

        return articles
