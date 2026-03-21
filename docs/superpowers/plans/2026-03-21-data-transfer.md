# Data Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add runtime database import and dataset zip export to both the GUI and CLI.

**Architecture:** A dedicated data transfer service owns zip creation, SQLite validation, and database replacement. CLI and GUI become thin adapters that collect paths, confirm destructive actions, invoke the service, and refresh runtime state.

**Tech Stack:** Python stdlib (`pathlib`, `sqlite3`, `zipfile`, `shutil`, `tempfile`, `unittest`), Tkinter GUI, existing runtime path helpers.

---

### Task 1: Lock Service Behavior With Tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_data_transfer.py`

- [ ] **Step 1: Write the failing test**

Add tests for:
- zip export includes `articles.db`, `articles/html/...`, and `articles/markdown/...`
- db import replaces target database and writes a backup
- invalid database import raises an error

- [ ] **Step 2: Run test to verify it fails**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_data_transfer -v`
Expected: FAIL because `services.data_transfer` does not exist yet.

- [ ] **Step 3: Commit**

Skip unless explicitly requested by the user.

### Task 2: Implement Service Layer

**Files:**
- Create: `services/data_transfer.py`

- [ ] **Step 1: Write minimal implementation**

Implement:
- runtime data path resolution helpers
- zip export with stable archive layout
- SQLite validation for imported `.db`
- backup + replacement logic for runtime database

- [ ] **Step 2: Run tests to verify they pass**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_data_transfer -v`
Expected: PASS

- [ ] **Step 3: Commit**

Skip unless explicitly requested by the user.

### Task 3: Add CLI Commands

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add `export-data` and `import-db` commands**

Expose service functions through CLI commands with clear usage text and success/error output.

- [ ] **Step 2: Run targeted smoke checks**

Use the conda Python interpreter to run one export command and one import validation command against temp fixtures.

- [ ] **Step 3: Commit**

Skip unless explicitly requested by the user.

### Task 4: Add GUI Menu Actions

**Files:**
- Modify: `gui/app.py`

- [ ] **Step 1: Add file menu entries**

Add:
- `导入数据库`
- `导出数据包`

- [ ] **Step 2: Implement handlers**

Handlers should:
- open the right file dialogs
- show replacement warning for import
- call the service layer
- refresh statistics and article list after import

- [ ] **Step 3: Run tests again**

Run: `C:\Users\alpha\.conda\envs\wechat-scraper\python.exe -m unittest tests.test_data_transfer -v`
Expected: PASS

- [ ] **Step 4: Commit**

Skip unless explicitly requested by the user.
