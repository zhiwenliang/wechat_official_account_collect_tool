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
