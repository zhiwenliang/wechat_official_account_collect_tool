"""
数据库操作模块
使用SQLite存储文章信息
"""
import sqlite3
from pathlib import Path
from datetime import datetime

from utils.runtime_env import resolve_runtime_path

class Database:
    EMPTY_CONTENT_CONDITION = "status = 'scraped' AND TRIM(COALESCE(content_html, '')) = ''"

    def __init__(self, db_path="data/articles.db"):
        if db_path == "data/articles.db":
            self.db_path = resolve_runtime_path(db_path)
        else:
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
                account_name TEXT,
                url TEXT UNIQUE NOT NULL,
                publish_time TEXT,
                scraped_at TEXT,
                status TEXT DEFAULT 'pending',
                file_path TEXT,
                content_html TEXT,
                content_markdown TEXT
            )
        """)

        self._migrate_articles_table(cursor)
        self._ensure_indexes(cursor)

        conn.commit()
        conn.close()

    def _migrate_articles_table(self, cursor):
        """为旧版本数据库补充缺失列"""
        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            "account_name": "TEXT",
            "content_html": "TEXT",
            "content_markdown": "TEXT",
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE articles ADD COLUMN {column_name} {column_type}"
                )

    def _ensure_indexes(self, cursor):
        """Create indexes used by list and statistics queries."""
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_status_id
            ON articles(status, id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_publish_time
            ON articles(publish_time)
        """)

    def _build_article_list_filters(self, status, search=""):
        """Build WHERE conditions and params for article list queries."""
        conditions = []
        params = []

        if status == "empty":
            conditions.append(self.EMPTY_CONTENT_CONDITION)
        elif status != "all":
            conditions.append("status = ?")
            params.append(status)

        if search:
            conditions.append("""
                (
                    LOWER(COALESCE(title, '')) LIKE ?
                    OR LOWER(COALESCE(url, '')) LIKE ?
                )
            """)
            search_pattern = f"%{search.lower()}%"
            params.extend([search_pattern, search_pattern])

        return conditions, params

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

    def get_article_status(self, url):
        """根据URL获取文章状态，不存在时返回None"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status FROM articles WHERE url = ?", (url,))
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

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

        cursor.execute(f"SELECT COUNT(*) FROM articles WHERE {self.EMPTY_CONTENT_CONDITION}")
        empty_content = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total,
            'pending': status_counts.get('pending', 0),
            'scraped': status_counts.get('scraped', 0),
            'failed': status_counts.get('failed', 0),
            'empty_content': empty_content,
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

    def get_empty_content_articles(self):
        """获取已抓取但正文为空的文章"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT id, url
            FROM articles
            WHERE {self.EMPTY_CONTENT_CONDITION}
            ORDER BY id
        """)
        articles = cursor.fetchall()
        conn.close()

        return articles

    def reset_empty_content(self):
        """将无内容文章重置为pending，便于重新抓取"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            UPDATE articles
            SET status = 'pending',
                scraped_at = NULL,
                file_path = NULL,
                content_html = NULL,
                content_markdown = NULL
            WHERE {self.EMPTY_CONTENT_CONDITION}
        """)
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    def get_article_by_id(self, article_id):
        """根据ID获取单篇文章详情（含正文）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, url, title, publish_time, scraped_at, file_path, status,
                   content_markdown,
                   CASE WHEN status = 'scraped' AND TRIM(COALESCE(content_html, '')) = '' THEN 1 ELSE 0 END AS is_empty_content
            FROM articles
            WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def get_articles_by_ids(self, article_ids):
        """根据ID获取文章基础信息"""
        if not article_ids:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(article_ids))
        cursor.execute(f"""
            SELECT id, url
            FROM articles
            WHERE id IN ({placeholders})
            ORDER BY id
        """, tuple(article_ids))
        rows = cursor.fetchall()
        conn.close()

        return rows

    def reset_articles_by_ids(self, article_ids):
        """将指定文章重置为pending，便于重新抓取"""
        if not article_ids:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(article_ids))
        cursor.execute(f"""
            UPDATE articles
            SET status = 'pending',
                scraped_at = NULL,
                file_path = NULL,
                content_html = NULL,
                content_markdown = NULL
            WHERE id IN ({placeholders})
        """, tuple(article_ids))
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    def delete_articles_by_ids(self, article_ids):
        """删除指定文章记录"""
        if not article_ids:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ",".join(["?"] * len(article_ids))
        cursor.execute(f"""
            DELETE FROM articles
            WHERE id IN ({placeholders})
        """, tuple(article_ids))
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        return affected

    def count_articles(self, status="all", search=""):
        """Count articles matching the current list filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM articles"
        conditions, params = self._build_article_list_filters(status, search)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor.execute(query, params)
        total = cursor.fetchone()[0]
        conn.close()

        return total

    def get_recent_articles(self, limit=5):
        """Return the most recent articles for the dashboard."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT id, title, publish_time, status,
                   CASE WHEN {self.EMPTY_CONTENT_CONDITION} THEN 1 ELSE 0 END AS is_empty_content
            FROM articles
            ORDER BY
                CASE WHEN TRIM(COALESCE(publish_time, '')) = '' THEN 1 ELSE 0 END ASC,
                publish_time DESC,
                id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return rows

    def get_articles_by_status(self, status, search="", sort_column=None, descending=False, limit=None, offset=0):
        """获取指定状态的文章列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = f"""
            SELECT id, url, title, publish_time, scraped_at, file_path, status,
                   CASE WHEN {self.EMPTY_CONTENT_CONDITION} THEN 1 ELSE 0 END AS is_empty_content
            FROM articles
        """
        conditions, params = self._build_article_list_filters(status, search)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        order_by_map = {
            "title": "COALESCE(title, '') COLLATE NOCASE",
            "publish_time": "COALESCE(publish_time, '')",
        }
        order_by = order_by_map.get(sort_column, "id")
        direction = "DESC" if descending else "ASC"
        query += f" ORDER BY {order_by} {direction}, id ASC"

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor.execute(query, params)
        articles = cursor.fetchall()
        conn.close()

        return articles
