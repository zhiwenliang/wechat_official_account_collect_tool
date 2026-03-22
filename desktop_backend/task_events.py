from __future__ import annotations

from typing import TypedDict


class TaskPrompt(TypedDict, total=False):
    step: str
    kind: str
    title: str
    message: str
    default_value: int
    min_value: int
    confirm_label: str
    reject_label: str


class TaskEvent(TypedDict, total=False):
    type: str
    task_id: str
    task_type: str
    message: str
    status: str
    reason: str
    current: int
    total: int
    success: int
    failed: int
    prompt: TaskPrompt


def _normalize_text(value: object) -> str:
    return "" if value is None else str(value)


def _normalize_int(value: object) -> int:
    return int(value)


def build_started_event(*, task_id: str, task_type: str) -> TaskEvent:
    return {
        "type": "started",
        "task_id": _normalize_text(task_id),
        "task_type": _normalize_text(task_type),
    }


def build_log_event(*, task_id: str, message: object) -> TaskEvent:
    return {
        "type": "log",
        "task_id": _normalize_text(task_id),
        "message": _normalize_text(message),
    }


def build_progress_event(
    *,
    task_id: str,
    current: object,
    total: object,
    message: object = "",
    success: object | None = None,
    failed: object | None = None,
) -> TaskEvent:
    event: TaskEvent = {
        "type": "progress",
        "task_id": _normalize_text(task_id),
        "current": _normalize_int(current),
        "total": _normalize_int(total),
        "message": _normalize_text(message),
    }
    if success is not None:
        event["success"] = _normalize_int(success)
    if failed is not None:
        event["failed"] = _normalize_int(failed)
    return event


def build_status_event(*, task_id: str, status: object, message: object = "") -> TaskEvent:
    return {
        "type": "status",
        "task_id": _normalize_text(task_id),
        "status": _normalize_text(status),
        "message": _normalize_text(message),
    }


def build_prompt_event(*, task_id: str, prompt: TaskPrompt) -> TaskEvent:
    normalized_prompt: TaskPrompt = {
        "step": _normalize_text(prompt.get("step")),
        "kind": _normalize_text(prompt.get("kind")),
        "title": _normalize_text(prompt.get("title")),
        "message": _normalize_text(prompt.get("message")),
    }
    if "default_value" in prompt and prompt["default_value"] is not None:
        normalized_prompt["default_value"] = _normalize_int(prompt["default_value"])
    if "min_value" in prompt and prompt["min_value"] is not None:
        normalized_prompt["min_value"] = _normalize_int(prompt["min_value"])
    if "confirm_label" in prompt:
        normalized_prompt["confirm_label"] = _normalize_text(prompt["confirm_label"])
    if "reject_label" in prompt:
        normalized_prompt["reject_label"] = _normalize_text(prompt["reject_label"])

    return {
        "type": "prompt",
        "task_id": _normalize_text(task_id),
        "prompt": normalized_prompt,
    }


def build_completed_event(*, task_id: str, task_type: str) -> TaskEvent:
    return {
        "type": "completed",
        "task_id": _normalize_text(task_id),
        "task_type": _normalize_text(task_type),
    }


def build_error_event(*, task_id: str, message: object) -> TaskEvent:
    return {
        "type": "error",
        "task_id": _normalize_text(task_id),
        "message": _normalize_text(message),
    }


def build_stopped_event(*, task_id: str, reason: object = "") -> TaskEvent:
    return {
        "type": "stopped",
        "task_id": _normalize_text(task_id),
        "reason": _normalize_text(reason),
    }


def build_cancelled_event(*, task_id: str, reason: object = "") -> TaskEvent:
    return {
        "type": "cancelled",
        "task_id": _normalize_text(task_id),
        "reason": _normalize_text(reason),
    }
