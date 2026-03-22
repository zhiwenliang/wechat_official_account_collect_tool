from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from threading import RLock

from .task_events import (
    TaskEvent,
    build_cancelled_event,
    build_completed_event,
    build_error_event,
    build_log_event,
    build_progress_event,
    build_started_event,
    build_status_event,
    build_stopped_event,
)


@dataclass
class _TaskState:
    task_id: str
    task_type: str
    active: bool = True
    stopping: bool = False
    events: list[TaskEvent] = field(default_factory=list)


class TaskRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._id_source = count(1)
        self._tasks: dict[str, _TaskState] = {}
        self._finished_tasks: dict[str, _TaskState] = {}

    def start_task(self, task_type: str) -> str:
        task_id = self._make_task_id(task_type)
        task = _TaskState(task_id=task_id, task_type=str(task_type))
        task.events.append(build_started_event(task_id=task_id, task_type=task.task_type))

        with self._lock:
            self._tasks[task_id] = task

        return task_id

    def record_log(self, task_id: str, message: object) -> TaskEvent:
        return self._append_event(task_id, build_log_event(task_id=task_id, message=message))

    def record_progress(
        self,
        task_id: str,
        current: object,
        total: object,
        message: object = "",
        *,
        success: object | None = None,
        failed: object | None = None,
    ) -> TaskEvent:
        return self._append_event(
            task_id,
            build_progress_event(
                task_id=task_id,
                current=current,
                total=total,
                message=message,
                success=success,
                failed=failed,
            ),
        )

    def record_status(self, task_id: str, status: object, message: object = "") -> TaskEvent:
        return self._append_event(
            task_id,
            build_status_event(task_id=task_id, status=status, message=message),
        )

    def record_completed(self, task_id: str) -> TaskEvent:
        with self._lock:
            state = self._require_task_unlocked(task_id)
            event = build_completed_event(task_id=state.task_id, task_type=state.task_type)
            return self._finalize_task_unlocked(task_id, event)

    def record_error(self, task_id: str, message: object) -> TaskEvent:
        with self._lock:
            state = self._require_task_unlocked(task_id)
            event = build_error_event(task_id=state.task_id, message=message)
            return self._finalize_task_unlocked(task_id, event)

    def record_stopped(self, task_id: str, reason: object = "") -> TaskEvent:
        with self._lock:
            state = self._require_task_unlocked(task_id)
            state.stopping = True
            return self._finalize_task_unlocked(
                task_id,
                build_stopped_event(task_id=task_id, reason=reason),
            )

    def record_cancelled(self, task_id: str, reason: object = "") -> TaskEvent:
        with self._lock:
            state = self._require_task_unlocked(task_id)
            state.stopping = True
            return self._finalize_task_unlocked(
                task_id,
                build_cancelled_event(task_id=task_id, reason=reason),
            )

    def request_stop(self, task_id: str) -> None:
        with self._lock:
            state = self._tasks.get(task_id)
            if state is None:
                return
            state.stopping = True

    def should_stop(self, task_id: str) -> bool:
        with self._lock:
            state = self._tasks.get(task_id)
            return bool(state and state.stopping)

    def is_stopping(self, task_id: str) -> bool:
        return self.should_stop(task_id)

    def is_active(self, task_id: str) -> bool:
        with self._lock:
            state = self._tasks.get(task_id)
            return bool(state and state.active)

    def get_task(self, task_id: str) -> _TaskState | None:
        with self._lock:
            state = self._tasks.get(task_id)
            if state is None:
                return None
            return _TaskState(
                task_id=state.task_id,
                task_type=state.task_type,
                active=state.active,
                stopping=state.stopping,
                events=list(state.events),
            )

    def snapshot_task(self, task_id: str) -> _TaskState | None:
        with self._lock:
            state = self._tasks.get(task_id)
            if state is None:
                state = self._finished_tasks.get(task_id)
            if state is None:
                return None
            return _TaskState(
                task_id=state.task_id,
                task_type=state.task_type,
                active=state.active,
                stopping=state.stopping,
                events=list(state.events),
            )

    def drain_events(self, task_id: str) -> list[TaskEvent]:
        with self._lock:
            state = self._tasks.get(task_id)
            if state is None:
                state = self._finished_tasks.get(task_id)
            if state is None:
                return []
            events = list(state.events)
            state.events.clear()
            if task_id in self._finished_tasks:
                self._finished_tasks.pop(task_id, None)
            return events

    def complete_task(self, task_id: str) -> TaskEvent:
        return self.record_completed(task_id)

    def discard_task(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)
            self._finished_tasks.pop(task_id, None)

    def _append_event(self, task_id: str, event: TaskEvent) -> TaskEvent:
        with self._lock:
            state = self._require_task_unlocked(task_id)
            state.events.append(event)
        return event

    def _finalize_task_unlocked(self, task_id: str, event: TaskEvent) -> TaskEvent:
        state = self._require_task_unlocked(task_id)
        state.events.append(event)
        state.active = False
        self._finished_tasks[task_id] = state
        self._tasks.pop(task_id, None)
        return event

    def _require_task_unlocked(self, task_id: str) -> _TaskState:
        state = self._tasks.get(task_id)
        if state is None:
            raise KeyError(f"Unknown task id: {task_id}")
        return state

    def _make_task_id(self, task_type: str) -> str:
        with self._lock:
            counter = next(self._id_source)
        normalized = "-".join(str(task_type).strip().split()) or "task"
        return f"{normalized}-{counter}"
