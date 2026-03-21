# Data Transfer Design

**Feature:** database import plus dataset export for the desktop GUI and CLI.

## Scope

- Export the current runtime dataset as one `.zip` bundle.
- The bundle includes:
  - `articles.db`
  - `articles/html/`
  - `articles/markdown/`
- Import only supports selecting an external `.db` file and replacing the current runtime database.

## Approach

- Add a small service module dedicated to data transfer operations.
- Keep GUI and CLI thin: they only gather file paths, confirm risk, call the service, and display results.
- Reuse runtime path resolution so packaged builds and source runs behave the same way.

## Data Flow

### Export

1. Resolve the runtime database path and article backup directories.
2. Create a zip archive chosen by the user.
3. Add the database file as `articles.db`.
4. Recursively add existing HTML and Markdown backup files under `articles/`.
5. Return counts and archive path for user-facing messages.

### Import

1. User selects a `.db` file.
2. Validate that the selected file is a readable SQLite database with an `articles` table.
3. Backup the current runtime database to a timestamped backup database file in the same directory.
4. Copy the selected `.db` over the runtime `data/articles.db`.
5. Refresh GUI statistics and article list.

## Error Handling

- Export fails if the runtime database file does not exist.
- Export tolerates missing `articles/html` or `articles/markdown` directories and simply skips them.
- Import fails fast for missing files, wrong suffixes, unreadable SQLite files, or databases without an `articles` table.
- Import warns that replacing only the database may leave HTML/Markdown backups out of sync with database rows.

## Interfaces

- `services/data_transfer.py`
  - `export_data_bundle(output_path, db_path=None, articles_dir=None)`
  - `import_database_file(source_db_path, target_db_path=None)`
- `main.py`
  - `python main.py export-data <zip_path>`
  - `python main.py import-db <db_path>`
- `gui/app.py`
  - File menu items for `导入数据库` and `导出数据包`

## Verification

- Add focused `unittest` coverage for:
  - zip archive structure and file inclusion
  - database replacement plus backup creation
  - invalid import database rejection
