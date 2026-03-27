from typing import Any, TypedDict


class RecentArticlePayload(TypedDict):
    id: int
    title: str
    publish_time: str
    status: str
    is_empty_content: int


class ArticlePayload(TypedDict):
    id: int
    url: str
    title: str
    publish_time: str
    scraped_at: str
    file_path: str
    status: str
    is_empty_content: int


class ArticleDetailPayload(TypedDict):
    id: int
    url: str
    title: str
    publish_time: str
    scraped_at: str
    file_path: str
    status: str
    is_empty_content: int
    content_markdown: str


class ArticlesPayload(TypedDict):
    total: int
    page: int
    page_size: int
    items: list[ArticlePayload]


def build_recent_article_payload(row: tuple[Any, ...]) -> RecentArticlePayload:
    article_id, title, publish_time, status, is_empty_content = row
    return {
        "id": int(article_id),
        "title": title or "",
        "publish_time": publish_time or "",
        "status": status or "",
        "is_empty_content": int(is_empty_content),
    }


def build_article_payload(row: tuple[Any, ...]) -> ArticlePayload:
    article_id, url, title, publish_time, scraped_at, file_path, status, is_empty_content = row
    return {
        "id": int(article_id),
        "url": url or "",
        "title": title or "",
        "publish_time": publish_time or "",
        "scraped_at": scraped_at or "",
        "file_path": file_path or "",
        "status": status or "",
        "is_empty_content": int(is_empty_content),
    }


def build_articles_payload(
    *,
    total: int,
    page: int,
    page_size: int,
    items: list[tuple[Any, ...]],
) -> ArticlesPayload:
    return {
        "total": int(total),
        "page": int(page),
        "page_size": int(page_size),
        "items": [build_article_payload(row) for row in items],
    }


def build_article_detail_payload(row: tuple[Any, ...]) -> ArticleDetailPayload:
    (
        article_id,
        url,
        title,
        publish_time,
        scraped_at,
        file_path,
        status,
        content_markdown,
        is_empty_content,
    ) = row
    return {
        "id": int(article_id),
        "url": url or "",
        "title": title or "",
        "publish_time": publish_time or "",
        "scraped_at": scraped_at or "",
        "file_path": file_path or "",
        "status": status or "",
        "is_empty_content": int(is_empty_content),
        "content_markdown": content_markdown or "",
    }
