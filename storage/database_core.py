"""SQLite connection, schema creation, migrations, and index helpers."""

import sqlite3
from pathlib import Path

EMPTY_CONTENT_CONDITION = (
    "status = 'scraped' AND TRIM(COALESCE(content_html, '')) = ''"
)


def connect_db(db_path):
    """Open a SQLite connection to the given database path."""
    return sqlite3.connect(db_path)


def create_articles_table(cursor):
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


def migrate_articles_table(cursor):
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


def ensure_indexes(cursor):
    """Create indexes used by list and statistics queries."""
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_status_id
        ON articles(status, id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_publish_time
        ON articles(publish_time)
    """)


def initialize_database(db_path: Path) -> None:
    """Create schema, run migrations, and ensure indexes."""
    conn = connect_db(db_path)
    try:
        cursor = conn.cursor()
        create_articles_table(cursor)
        migrate_articles_table(cursor)
        ensure_indexes(cursor)
        conn.commit()
    finally:
        conn.close()
