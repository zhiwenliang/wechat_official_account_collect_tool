from __future__ import annotations

from typing import TypedDict


class TaskEvent(TypedDict, total=False):
    type: str
    task_id: str
    task_type: str
    message: str
    status: str
    reason: str
    current: int
    total: int


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


def build_progress_event(*, task_id: str, current: object, total: object, message: object = "") -> TaskEvent:
    return {
        "type": "progress",
        "task_id": _normalize_text(task_id),
        "current": _normalize_int(current),
        "total": _normalize_int(total),
        "message": _normalize_text(message),
    }


def build_status_event(*, task_id: str, status: object, message: object = "") -> TaskEvent:
    return {
        "type": "status",
        "task_id": _normalize_text(task_id),
        "status": _normalize_text(status),
        "message": _normalize_text(message),
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
