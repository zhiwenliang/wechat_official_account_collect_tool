"""Article insert, update, reset, and delete helpers."""

import sqlite3

from storage.database_core import EMPTY_CONTENT_CONDITION, connect_db


def add_article(db_path, url, status="pending"):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO articles (url, status) VALUES (?, ?)",
            (url, status),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def update_article(db_path, url, **kwargs):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [url]

    cursor.execute(f"UPDATE articles SET {fields} WHERE url = ?", values)
    conn.commit()
    conn.close()


def reset_failed(db_path):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE articles SET status = 'pending' WHERE status = 'failed'")
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    return affected


def reset_empty_content(db_path):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        UPDATE articles
        SET status = 'pending',
            scraped_at = NULL,
            file_path = NULL,
            content_html = NULL,
            content_markdown = NULL
        WHERE {EMPTY_CONTENT_CONDITION}
    """)
    affected = cursor.rowcount
    conn.commit()
    conn.close()

    return affected


def reset_articles_by_ids(db_path, article_ids):
    if not article_ids:
        return 0

    conn = connect_db(db_path)
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


def delete_articles_by_ids(db_path, article_ids):
    if not article_ids:
        return 0

    conn = connect_db(db_path)
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
