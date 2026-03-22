from __future__ import annotations

from pathlib import Path
from typing import Any

from services.data_transfer import export_data_bundle, import_database_file


def export_data_bundle_handler(
    *,
    output_path: str | Path,
    db_path: str | Path | None = None,
    articles_dir: str | Path | None = None,
) -> dict[str, Any]:
    result = export_data_bundle(output_path, db_path=db_path, articles_dir=articles_dir)
    return {
        "archive_path": str(result.archive_path),
        "file_count": result.file_count,
    }


def import_database_handler(
    *,
    source_db_path: str | Path,
    target_db_path: str | Path | None = None,
) -> dict[str, Any]:
    result = import_database_file(source_db_path, target_db_path=target_db_path)
    return {
        "source_db_path": str(result.source_db_path),
        "target_db_path": str(result.target_db_path),
        "backup_path": str(result.backup_path) if result.backup_path is not None else None,
    }
