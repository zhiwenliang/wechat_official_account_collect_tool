from __future__ import annotations

import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from utils.runtime_env import resolve_runtime_path

REQUIRED_ARTICLE_COLUMNS = {
    "id",
    "title",
    "url",
    "publish_time",
    "scraped_at",
    "status",
    "file_path",
    "content_html",
    "content_markdown",
}


@dataclass
class ExportDataResult:
    archive_path: Path
    file_count: int


@dataclass
class ImportDatabaseResult:
    source_db_path: Path
    target_db_path: Path
    backup_path: Path | None


def get_runtime_database_path() -> Path:
    return resolve_runtime_path("data/articles.db")


def get_runtime_articles_path() -> Path:
    return resolve_runtime_path("data/articles")


def _normalize_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _iter_article_backup_files(articles_dir: Path, excluded_paths: set[Path] | None = None):
    excluded_paths = excluded_paths or set()
    for relative_root in (Path("html"), Path("markdown")):
        root = articles_dir / relative_root
        if not root.exists():
            continue
        for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
            normalized = file_path.resolve()
            if normalized in excluded_paths:
                continue
            yield file_path


def _validate_articles_database(db_path: Path) -> None:
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        raise ValueError(f"无法读取 SQLite 数据库: {db_path}") from exc

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'articles'"
        )
        if cursor.fetchone() is None:
            raise ValueError("选择的数据库缺少 articles 表")
        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        missing_columns = sorted(REQUIRED_ARTICLE_COLUMNS - existing_columns)
        if missing_columns:
            missing_text = ", ".join(missing_columns)
            raise ValueError(f"articles 表缺少必要列: {missing_text}")
    finally:
        conn.close()


def export_data_bundle(
    output_path: str | Path,
    db_path: str | Path | None = None,
    articles_dir: str | Path | None = None,
) -> ExportDataResult:
    db_path = _normalize_path(db_path or get_runtime_database_path())
    articles_dir = _normalize_path(articles_dir or get_runtime_articles_path())
    output_path = _normalize_path(output_path)

    if not db_path.exists():
        raise FileNotFoundError(f"数据库文件不存在: {db_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_count = 0
    excluded_paths = {output_path}
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(db_path, "articles.db")
        file_count += 1

        for file_path in _iter_article_backup_files(articles_dir, excluded_paths=excluded_paths):
            archive_name = (Path("articles") / file_path.relative_to(articles_dir)).as_posix()
            archive.write(file_path, archive_name)
            file_count += 1

    return ExportDataResult(archive_path=output_path, file_count=file_count)


def import_database_file(
    source_db_path: str | Path,
    target_db_path: str | Path | None = None,
) -> ImportDatabaseResult:
    source_db_path = _normalize_path(source_db_path)
    target_db_path = _normalize_path(target_db_path or get_runtime_database_path())

    if source_db_path.suffix.lower() != ".db":
        raise ValueError("请选择 .db 数据库文件")
    if not source_db_path.exists():
        raise FileNotFoundError(f"数据库文件不存在: {source_db_path}")
    if source_db_path == target_db_path:
        raise ValueError("不能导入当前正在使用的数据库文件")

    _validate_articles_database(source_db_path)

    target_db_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = None
    if target_db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = target_db_path.with_name(
            f"{target_db_path.stem}.backup-{timestamp}{target_db_path.suffix}"
        )
        shutil.copy2(target_db_path, backup_path)

    shutil.copy2(source_db_path, target_db_path)
    _validate_articles_database(target_db_path)

    return ImportDatabaseResult(
        source_db_path=source_db_path,
        target_db_path=target_db_path,
        backup_path=backup_path,
    )
