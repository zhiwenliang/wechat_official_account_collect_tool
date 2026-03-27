"""
数据库操作模块
使用SQLite存储文章信息
"""
from storage.database_core import (
    EMPTY_CONTENT_CONDITION,
    ensure_database_parent_dir,
    initialize_database,
    resolve_articles_db_path,
)
from storage.database_mutations import (
    add_article as _add_article,
    delete_articles_by_ids as _delete_articles_by_ids,
    reset_articles_by_ids as _reset_articles_by_ids,
    reset_empty_content as _reset_empty_content,
    reset_failed as _reset_failed,
    update_article as _update_article,
)
from storage.database_queries import (
    build_article_list_filters as _build_article_list_filters,
    count_articles as _count_articles,
    get_article_by_id as _get_article_by_id,
    get_article_status as _get_article_status,
    get_articles_by_ids as _get_articles_by_ids,
    get_articles_by_status as _get_articles_by_status,
    get_empty_content_articles as _get_empty_content_articles,
    get_pending_articles as _get_pending_articles,
    get_recent_articles as _get_recent_articles,
    get_statistics as _get_statistics,
    url_exists as _url_exists,
)


def _bind_db_path(impl, doc=None):
    def bound(self, *args, **kwargs):
        return impl(self.db_path, *args, **kwargs)

    bound.__name__ = impl.__name__
    bound.__doc__ = doc if doc is not None else impl.__doc__
    return bound


class Database:
    EMPTY_CONTENT_CONDITION = EMPTY_CONTENT_CONDITION

    def __init__(self, db_path="data/articles.db"):
        self.db_path = resolve_articles_db_path(db_path)
        ensure_database_parent_dir(self.db_path)
        initialize_database(self.db_path)

    def _build_article_list_filters(self, status, search=""):
        return _build_article_list_filters(status, search)

    def add_article(self, url, status="pending"):
        """添加文章链接"""
        return _add_article(self.db_path, url, status)

    def update_article(self, url, **kwargs):
        """更新文章信息"""
        return _update_article(self.db_path, url, **kwargs)

    def get_pending_articles(self):
        """获取待抓取的文章"""
        return _get_pending_articles(self.db_path)

    def url_exists(self, url):
        """检查URL是否已存在"""
        return _url_exists(self.db_path, url)

    def get_article_status(self, url):
        """根据URL获取文章状态，不存在时返回None"""
        return _get_article_status(self.db_path, url)

    def get_statistics(self):
        """获取统计信息"""
        return _get_statistics(self.db_path)

    def reset_failed(self):
        """重置失败的文章状态为pending"""
        return _reset_failed(self.db_path)

    def get_empty_content_articles(self):
        """获取已抓取但正文为空的文章"""
        return _get_empty_content_articles(self.db_path)

    def reset_empty_content(self):
        """将无内容文章重置为pending，便于重新抓取"""
        return _reset_empty_content(self.db_path)

    def get_article_by_id(self, article_id):
        """根据ID获取单篇文章详情（含正文）"""
        return _get_article_by_id(self.db_path, article_id)

    def get_articles_by_ids(self, article_ids):
        """根据ID获取文章基础信息"""
        return _get_articles_by_ids(self.db_path, article_ids)

    def reset_articles_by_ids(self, article_ids):
        """将指定文章重置为pending，便于重新抓取"""
        return _reset_articles_by_ids(self.db_path, article_ids)

    delete_articles_by_ids = _bind_db_path(
        _delete_articles_by_ids, doc="删除指定文章记录"
    )

    def count_articles(self, status="all", search=""):
        """Count articles matching the current list filters."""
        return _count_articles(self.db_path, status, search)

    def get_recent_articles(self, limit=5):
        """Return the most recent articles for the dashboard."""
        return _get_recent_articles(self.db_path, limit)

    get_articles_by_status = _bind_db_path(
        _get_articles_by_status, doc="获取指定状态的文章列表"
    )
