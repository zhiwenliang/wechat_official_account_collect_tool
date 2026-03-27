# Codebase Structure Phase 1 Boundary Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the first stable structure boundaries for shared desktop contracts, backend HTTP helpers, and backend task packages without changing product behavior or breaking current entry points.

**Architecture:** Phase 1 does not do the heavy file splits from the approved structure spec. Instead, it creates the package seams that later phases will expand: `desktop/src/shared/` for cross-runtime desktop contracts, `desktop_backend/http/` for HTTP-specific helpers, and `desktop_backend/tasks/` for task-oriented backend imports. Current entry points stay valid while new package boundaries become the preferred import paths.

**Tech Stack:** TypeScript, Electron, React, Vitest, Python 3.10, `unittest`, existing `desktop_backend` runtime modules, ripgrep for import verification.

---

## File Structure

- Create: `desktop/src/shared/desktop-contract.ts`
  - Shared `BackendHealth`, `BackendStatus`, and `DesktopBridge` contract used by Electron and renderer.
- Create: `desktop/src/shared/desktop-contract.test.ts`
  - Type-level regression coverage for the shared desktop contract module.
- Modify: `desktop/electron/main.ts`
  - Stop importing backend status types from a renderer-owned path.
- Modify: `desktop/src/renderer/App.tsx`
  - Import `BackendStatus` from the shared desktop contract module.
- Modify: `desktop/src/renderer/lib/api.ts`
  - Import `BackendStatus` and `DesktopBridge` from the shared desktop contract module.
- Modify: `desktop/src/renderer/lib/task-events.ts`
  - Remove backend connection types that no longer belong in a renderer task-events module.

- Create: `desktop_backend/http/__init__.py`
  - Preferred import surface for new HTTP helper modules.
- Create: `desktop_backend/http/parsing.py`
  - Shared query parsing helpers extracted from `desktop_backend/server.py`.
- Create: `desktop_backend/http/image_proxy.py`
  - Shared image proxy validation and response-size helpers extracted from `desktop_backend/server.py`.
- Modify: `desktop_backend/server.py`
  - Consume the new HTTP helper modules while keeping `DesktopBackendServer` at the current import path for this phase.

- Create: `desktop_backend/tasks/__init__.py`
  - Preferred import surface for task-related runtime objects.
- Create: `desktop_backend/tasks/events.py`
  - Re-export task event builders from the existing module.
- Create: `desktop_backend/tasks/registry.py`
  - Re-export `TaskRegistry` from the existing module.
- Create: `desktop_backend/tasks/handlers.py`
  - Re-export `WorkflowTaskHandlers` from the existing module.
- Modify: `desktop_backend/app.py`
  - Switch the app composition layer to use the new `desktop_backend.tasks.*` paths.

- Create: `tests/test_desktop_backend_structure.py`
  - Structural regression coverage proving the new HTTP/task package boundaries exist and preserve import compatibility.

### Task 1: Extract Shared Desktop Contract Types

**Files:**
- Create: `desktop/src/shared/desktop-contract.test.ts`
- Create: `desktop/src/shared/desktop-contract.ts`
- Modify: `desktop/electron/main.ts`
- Modify: `desktop/src/renderer/App.tsx`
- Modify: `desktop/src/renderer/lib/api.ts`
- Modify: `desktop/src/renderer/lib/task-events.ts`
- Test: `desktop/src/shared/desktop-contract.test.ts`

- [ ] **Step 1: Write the failing shared-contract test**

Create `desktop/src/shared/desktop-contract.test.ts` with this exact content:

```typescript
import { describe, expectTypeOf, it } from "vitest";

import type {
  BackendHealth,
  BackendStatus,
  DesktopBridge,
} from "./desktop-contract";

describe("desktop-contract", () => {
  it("defines the shared backend status and preload bridge contract", () => {
    expectTypeOf<BackendHealth>().toEqualTypeOf<{
      status: "ok";
      service: string;
    }>();

    expectTypeOf<BackendStatus>().toMatchTypeOf<
      | {
          state: "starting";
          message: string;
        }
      | {
          state: "ready";
          baseUrl: string;
          health: BackendHealth;
        }
      | {
          state: "error";
          message: string;
        }
    >();

    expectTypeOf<DesktopBridge>().toMatchTypeOf<{
      getBackendStatus: () => Promise<BackendStatus>;
    }>();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm --prefix desktop run test -- --run src/shared/desktop-contract.test.ts`

Expected: FAIL because `desktop/src/shared/desktop-contract.ts` does not exist yet.

- [ ] **Step 3: Write the minimal shared contract module and switch imports**

Create `desktop/src/shared/desktop-contract.ts` with this exact content:

```typescript
export type BackendHealth = {
  status: "ok";
  service: string;
};

export type BackendStatus =
  | {
      state: "starting";
      message: string;
    }
  | {
      state: "ready";
      baseUrl: string;
      health: BackendHealth;
    }
  | {
      state: "error";
      message: string;
    };

export interface DesktopBridge {
  getBackendStatus: () => Promise<BackendStatus>;
}

declare global {
  interface Window {
    desktop?: DesktopBridge;
  }
}
```

Update the imports exactly like this:

```typescript
// desktop/electron/main.ts
- import type { BackendHealth, BackendStatus } from "../src/renderer/lib/task-events";
+ import type { BackendHealth, BackendStatus } from "../src/shared/desktop-contract";

// desktop/src/renderer/App.tsx
- import type { BackendStatus } from "./lib/task-events";
+ import type { BackendStatus } from "../shared/desktop-contract";

// desktop/src/renderer/lib/api.ts
- import type { BackendStatus, TaskSnapshotPayload } from "./task-events";
+ import type { TaskSnapshotPayload } from "./task-events";
+ import type { BackendStatus, DesktopBridge } from "../shared/desktop-contract";

- export interface DesktopBridge {
-   getBackendStatus: () => Promise<BackendStatus>;
- }
-
- declare global {
-   interface Window {
-     desktop?: DesktopBridge;
-   }
- }
```

Remove the `BackendHealth` and `BackendStatus` declarations from `desktop/src/renderer/lib/task-events.ts` so that file only owns task-event types.

- [ ] **Step 4: Run the focused test and desktop typecheck**

Run:

```bash
npm --prefix desktop run test -- --run src/shared/desktop-contract.test.ts
npm --prefix desktop run typecheck
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desktop/src/shared/desktop-contract.ts desktop/src/shared/desktop-contract.test.ts desktop/electron/main.ts desktop/src/renderer/App.tsx desktop/src/renderer/lib/api.ts desktop/src/renderer/lib/task-events.ts
git commit -m "refactor: extract shared desktop contract types"
```

### Task 2: Introduce the Backend HTTP Helper Package

**Files:**
- Create: `tests/test_desktop_backend_structure.py`
- Create: `desktop_backend/http/__init__.py`
- Create: `desktop_backend/http/parsing.py`
- Create: `desktop_backend/http/image_proxy.py`
- Modify: `desktop_backend/server.py`
- Test: `tests/test_desktop_backend_structure.py`
- Verify: `tests/test_desktop_backend_server.py`

- [ ] **Step 1: Write the failing HTTP package structure test**

Create `tests/test_desktop_backend_structure.py` with this exact starting content:

```python
import unittest


class DesktopBackendStructureTests(unittest.TestCase):
    def test_http_helper_modules_exist(self) -> None:
        from desktop_backend.http.image_proxy import (
            IMAGE_PROXY_MAX_BYTES,
            validate_image_proxy_url,
        )
        from desktop_backend.http.parsing import parse_bool, parse_int

        self.assertEqual(parse_int({"page": ["7"]}, "page", 1), 7)
        self.assertTrue(parse_bool({"descending": ["true"]}, "descending"))
        self.assertEqual(
            validate_image_proxy_url("https://mmbiz.qpic.cn/image.png"),
            "https://mmbiz.qpic.cn/image.png",
        )
        self.assertEqual(IMAGE_PROXY_MAX_BYTES, 5 * 1024 * 1024)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure.DesktopBackendStructureTests.test_http_helper_modules_exist -v`

Expected: FAIL with `ModuleNotFoundError` because `desktop_backend.http` does not exist yet.

- [ ] **Step 3: Create the HTTP helper package and route `server.py` through it**

Create `desktop_backend/http/__init__.py`:

```python
from .image_proxy import (
    IMAGE_PROXY_ALLOWED_HOSTS,
    IMAGE_PROXY_ALLOWED_HOST_SUFFIXES,
    IMAGE_PROXY_MAX_BYTES,
    ImageProxyRequestError,
    read_image_proxy_response,
    validate_image_proxy_url,
)
from .parsing import parse_bool, parse_int

__all__ = [
    "IMAGE_PROXY_ALLOWED_HOSTS",
    "IMAGE_PROXY_ALLOWED_HOST_SUFFIXES",
    "IMAGE_PROXY_MAX_BYTES",
    "ImageProxyRequestError",
    "parse_bool",
    "parse_int",
    "read_image_proxy_response",
    "validate_image_proxy_url",
]
```

Create `desktop_backend/http/parsing.py`:

```python
from __future__ import annotations


def parse_int(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(query.get(key, [default])[0])
    except (TypeError, ValueError):
        return default


def parse_bool(query: dict[str, list[str]], key: str) -> bool:
    value = query.get(key, ["false"])[0]
    return str(value).lower() in {"1", "true", "yes", "on"}
```

Create `desktop_backend/http/image_proxy.py`:

```python
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

IMAGE_PROXY_MAX_BYTES = 5 * 1024 * 1024
IMAGE_PROXY_ALLOWED_HOSTS = {"res.wx.qq.com"}
IMAGE_PROXY_ALLOWED_HOST_SUFFIXES = (".qpic.cn", ".qlogo.cn", ".weixin.qq.com")


class ImageProxyRequestError(ValueError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def validate_image_proxy_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    hostname = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or not hostname:
        raise ImageProxyRequestError(400, "unsupported image url")

    if hostname in IMAGE_PROXY_ALLOWED_HOSTS or hostname.endswith(IMAGE_PROXY_ALLOWED_HOST_SUFFIXES):
        return parsed.geturl()

    raise ImageProxyRequestError(400, "unsupported image url")


def read_image_proxy_response(response: Any) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError:
            parsed_length = None
        if parsed_length is not None and parsed_length > IMAGE_PROXY_MAX_BYTES:
            raise ImageProxyRequestError(413, "image too large")

    data = response.read(IMAGE_PROXY_MAX_BYTES + 1)
    if len(data) > IMAGE_PROXY_MAX_BYTES:
        raise ImageProxyRequestError(413, "image too large")
    return data
```

Update `desktop_backend/server.py` imports and helper calls exactly like this:

```python
- from urllib.parse import parse_qs, urlsplit
+ from urllib.parse import parse_qs, urlsplit
+
+ from .http.image_proxy import (
+     IMAGE_PROXY_ALLOWED_HOSTS,
+     IMAGE_PROXY_ALLOWED_HOST_SUFFIXES,
+     IMAGE_PROXY_MAX_BYTES,
+     ImageProxyRequestError,
+     read_image_proxy_response,
+     validate_image_proxy_url,
+ )
+ from .http.parsing import parse_bool, parse_int
```

```python
- validated_url = _validate_image_proxy_url(url)
+ validated_url = validate_image_proxy_url(url)

- data = _read_image_proxy_response(resp)
+ data = read_image_proxy_response(resp)
```

Then remove the local `_parse_int`, `_parse_bool`, `_validate_image_proxy_url`, and `_read_image_proxy_response` implementations from `desktop_backend/server.py`.

- [ ] **Step 4: Run the focused structure test and the existing backend server suite**

Run:

```bash
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure.DesktopBackendStructureTests.test_http_helper_modules_exist -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_server -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_desktop_backend_structure.py desktop_backend/http/__init__.py desktop_backend/http/parsing.py desktop_backend/http/image_proxy.py desktop_backend/server.py
git commit -m "refactor: introduce desktop backend http helpers"
```

### Task 3: Introduce the Backend Tasks Package

**Files:**
- Modify: `tests/test_desktop_backend_structure.py`
- Create: `desktop_backend/tasks/__init__.py`
- Create: `desktop_backend/tasks/events.py`
- Create: `desktop_backend/tasks/registry.py`
- Create: `desktop_backend/tasks/handlers.py`
- Modify: `desktop_backend/app.py`
- Test: `tests/test_desktop_backend_structure.py`
- Verify: `tests/test_desktop_backend_tasks.py`

- [ ] **Step 1: Extend the structure test with task package compatibility coverage**

Append this exact test method to `tests/test_desktop_backend_structure.py`:

```python
    def test_tasks_package_re_exports_existing_runtime_objects(self) -> None:
        from desktop_backend.task_events import build_started_event
        from desktop_backend.task_handlers import WorkflowTaskHandlers
        from desktop_backend.task_registry import TaskRegistry

        from desktop_backend.tasks.events import (
            build_started_event as packaged_build_started_event,
        )
        from desktop_backend.tasks.handlers import (
            WorkflowTaskHandlers as packaged_workflow_task_handlers,
        )
        from desktop_backend.tasks.registry import (
            TaskRegistry as packaged_task_registry,
        )

        self.assertIs(build_started_event, packaged_build_started_event)
        self.assertIs(TaskRegistry, packaged_task_registry)
        self.assertIs(WorkflowTaskHandlers, packaged_workflow_task_handlers)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure.DesktopBackendStructureTests.test_tasks_package_re_exports_existing_runtime_objects -v`

Expected: FAIL with `ModuleNotFoundError` because `desktop_backend.tasks` does not exist yet.

- [ ] **Step 3: Create the package shims and switch the app composition layer**

Create `desktop_backend/tasks/__init__.py`:

```python
from .events import *
from .handlers import WorkflowTaskHandlers
from .registry import TaskRegistry
```

Create `desktop_backend/tasks/events.py`:

```python
from ..task_events import *
```

Create `desktop_backend/tasks/registry.py`:

```python
from ..task_registry import TaskRegistry

__all__ = ["TaskRegistry"]
```

Create `desktop_backend/tasks/handlers.py`:

```python
from ..task_handlers import WorkflowTaskHandlers

__all__ = ["WorkflowTaskHandlers"]
```

Update `desktop_backend/app.py` imports exactly like this:

```python
- from .task_handlers import WorkflowTaskHandlers
- from .task_registry import TaskRegistry
+ from .tasks.handlers import WorkflowTaskHandlers
+ from .tasks.registry import TaskRegistry
```

- [ ] **Step 4: Run the structure test and the task-focused backend tests**

Run:

```bash
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure.DesktopBackendStructureTests.test_tasks_package_re_exports_existing_runtime_objects -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_tasks -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_desktop_backend_structure.py desktop_backend/tasks/__init__.py desktop_backend/tasks/events.py desktop_backend/tasks/registry.py desktop_backend/tasks/handlers.py desktop_backend/app.py
git commit -m "refactor: add desktop backend task package seams"
```

### Task 4: Verify the Whole Phase 1 Boundary Extraction

**Files:**
- Modify only the specific touched files from Tasks 1-3 if verification reveals import drift

- [ ] **Step 1: Run the targeted Python verification suite**

Run:

```bash
conda run -n wechat-scraper python -m unittest \
  tests.test_desktop_backend_structure \
  tests.test_desktop_backend_server \
  tests.test_desktop_backend_queries \
  tests.test_desktop_backend_tasks -v
```

Expected: PASS

- [ ] **Step 2: Run the desktop verification suite**

Run:

```bash
npm --prefix desktop run typecheck
npm --prefix desktop run test
```

Expected: PASS

- [ ] **Step 3: Verify the boundary leak is gone and the new package seams are in use**

Run:

```bash
rg -n "src/renderer/lib/task-events" desktop/electron
rg -n "desktop_backend\\.http|desktop_backend\\.tasks" desktop_backend tests
```

Expected:

```text
First command: no matches
Second command: matches in `desktop_backend/app.py`, `desktop_backend/http/*`, `desktop_backend/tasks/*`, and `tests/test_desktop_backend_structure.py`
```

- [ ] **Step 4: Fix only the specific verification drift found**

If a verification command fails, apply only the smallest corrective edit. Use patterns like these:

```text
- Update one remaining import path to `../shared/desktop-contract`.
- Remove one stale helper copy left in `desktop_backend/server.py`.
- Correct one package import in `desktop_backend/app.py`.
```

Then re-run only the failed command before broad re-verification.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/shared desktop/src/renderer desktop/electron desktop_backend tests
git commit -m "chore: verify phase 1 boundary extraction"
```

## Phase 1 Completion Criteria

- `desktop/electron/main.ts` no longer imports backend status types from `desktop/src/renderer/lib/task-events`.
- `desktop/src/shared/desktop-contract.ts` exists and is the canonical home for shared desktop bridge/backend status types.
- `desktop_backend/http/` exists and owns parsing/image-proxy helpers now consumed by `desktop_backend/server.py`.
- `desktop_backend/tasks/` exists and provides stable package imports for task events, registry, and handlers.
- All current entry points still work with no behavior change:
  - `desktop/electron/main.ts`
  - `desktop/electron/preload.ts`
  - `desktop_backend/app.py`
