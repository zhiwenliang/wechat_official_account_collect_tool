"""Read-only article query helpers."""

from storage.database_core import EMPTY_CONTENT_CONDITION, connect_db


def build_article_list_filters(status, search=""):
    """Build WHERE conditions and params for article list queries."""
    conditions = []
    params = []

    if status == "empty":
        conditions.append(EMPTY_CONTENT_CONDITION)
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


def get_pending_articles(db_path):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, url FROM articles WHERE status = 'pending'")
    articles = cursor.fetchall()
    conn.close()

    return articles


def url_exists(db_path, url):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()

    return exists


def get_article_status(db_path, url):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM articles WHERE url = ?", (url,))
    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def get_statistics(db_path):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM articles")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM articles GROUP BY status")
    status_counts = dict(cursor.fetchall())

    cursor.execute("SELECT url FROM articles WHERE status = 'failed'")
    failed_urls = [row[0] for row in cursor.fetchall()]

    cursor.execute(f"SELECT COUNT(*) FROM articles WHERE {EMPTY_CONTENT_CONDITION}")
    empty_content = cursor.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "pending": status_counts.get("pending", 0),
        "scraped": status_counts.get("scraped", 0),
        "failed": status_counts.get("failed", 0),
        "empty_content": empty_content,
        "failed_urls": failed_urls,
    }


def get_empty_content_articles(db_path):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id, url
        FROM articles
        WHERE {EMPTY_CONTENT_CONDITION}
        ORDER BY id
    """)
    articles = cursor.fetchall()
    conn.close()

    return articles


def get_article_by_id(db_path, article_id):
    conn = connect_db(db_path)
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


def get_articles_by_ids(db_path, article_ids):
    if not article_ids:
        return []

    conn = connect_db(db_path)
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(article_ids))
    cursor.execute(f"""
        SELECT id, url, title, publish_time, scraped_at, file_path, status,
               CASE WHEN {EMPTY_CONTENT_CONDITION} THEN 1 ELSE 0 END AS is_empty_content
        FROM articles
        WHERE id IN ({placeholders})
        ORDER BY id
    """, tuple(article_ids))
    rows = cursor.fetchall()
    conn.close()

    return rows


def count_articles(db_path, status="all", search=""):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    query = "SELECT COUNT(*) FROM articles"
    conditions, params = build_article_list_filters(status, search)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)
    total = cursor.fetchone()[0]
    conn.close()

    return total


def get_recent_articles(db_path, limit=5):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id, title, publish_time, status,
               CASE WHEN {EMPTY_CONTENT_CONDITION} THEN 1 ELSE 0 END AS is_empty_content
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


def get_articles_by_status(
    db_path,
    status,
    search="",
    sort_column=None,
    descending=False,
    limit=None,
    offset=0,
):
    conn = connect_db(db_path)
    cursor = conn.cursor()

    query = f"""
        SELECT id, url, title, publish_time, scraped_at, file_path, status,
               CASE WHEN {EMPTY_CONTENT_CONDITION} THEN 1 ELSE 0 END AS is_empty_content
        FROM articles
    """
    conditions, params = build_article_list_filters(status, search)

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
