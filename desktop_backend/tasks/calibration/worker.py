from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

from services.calibration_service import CalibrationCancelled, run_desktop_calibration_action

if TYPE_CHECKING:
    from ...task_registry import TaskRegistry


class CalibrationTaskWorker:
    def __init__(self, *, task_id: str, task_registry: TaskRegistry, action: str, runtime) -> None:
        self.task_id = task_id
        self.task_registry = task_registry
        self.action = action
        self.runtime = runtime
        self._responses: queue.Queue[dict[str, object]] = queue.Queue()
        self._cancelled = threading.Event()

    def stop(self) -> None:
        self._cancelled.set()
        self.task_registry.clear_prompt(self.task_id)
        self._responses.put({"response": "__cancel__"})

    def should_stop(self) -> bool:
        return self._cancelled.is_set() or self.task_registry.should_stop(self.task_id)

    def submit_response(self, response: dict[str, object]) -> bool:
        if self.should_stop() or not self.task_registry.is_active(self.task_id):
            return False
        self._responses.put(dict(response))
        return True

    def run(self):
        return run_desktop_calibration_action(
            action=self.action,
            request_position=self._request_position,
            request_ack=self._request_ack,
            request_integer=self._request_integer,
            request_confirm=self._request_confirm,
            get_current_position=self.runtime.get_current_position,
            click=self.runtime.click,
            scroll=self.runtime.scroll,
            move_to=self.runtime.move_to,
            sleep=self.runtime.sleep,
            log=lambda message: self.task_registry.record_log(self.task_id, message),
            status=lambda message: self.task_registry.record_status(self.task_id, "waiting", message),
            stop_checker=self.should_stop,
        )

    def _request_position(self, step: str, title: str, message: str):
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "position",
                "title": title,
                "message": message,
            },
        )
        self._await_response({"record"})
        position = self.runtime.get_current_position()
        self.task_registry.record_status(
            self.task_id,
            "recorded",
            f"已记录当前位置：({int(position.x)}, {int(position.y)})",
        )
        return position

    def _request_ack(self, step: str, title: str, message: str) -> bool:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "ack",
                "title": title,
                "message": message,
            },
        )
        self._await_response({"continue"})
        self.task_registry.record_status(self.task_id, "acknowledged", "已确认，继续下一步。")
        return True

    def _request_integer(self, step: str, title: str, message: str, default_value: int, min_value: int) -> int:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "integer",
                "title": title,
                "message": message,
                "default_value": default_value,
                "min_value": min_value,
            },
        )
        while True:
            payload = self._await_response({"continue"}, clear_prompt=False)
            raw_value = payload.get("value")
            try:
                if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
                    raise ValueError("missing value")
                value = int(raw_value)
            except (TypeError, ValueError):
                self.task_registry.record_status(
                    self.task_id,
                    "invalid_response",
                    f"请输入大于等于 {min_value} 的整数。",
                )
                continue

            if value < min_value:
                self.task_registry.record_status(
                    self.task_id,
                    "invalid_response",
                    f"请输入大于等于 {min_value} 的整数。",
                )
                continue

            self.task_registry.clear_prompt(self.task_id)
            self.task_registry.record_status(self.task_id, "recorded", f"已记录数值：{value}")
            return value

    def _request_confirm(self, step: str, title: str, message: str, confirm_label: str, reject_label: str) -> bool:
        self.task_registry.record_prompt(
            self.task_id,
            {
                "step": step,
                "kind": "confirm",
                "title": title,
                "message": message,
                "confirm_label": confirm_label,
                "reject_label": reject_label,
            },
        )
        payload = self._await_response({"confirm"})
        accepted = bool(payload.get("accepted"))
        outcome = "已确认通过。" if accepted else "已确认未通过。"
        self.task_registry.record_status(self.task_id, "confirmed", outcome)
        return accepted

    def _await_response(self, allowed_responses: set[str], *, clear_prompt: bool = True) -> dict[str, object]:
        while True:
            if self.should_stop():
                raise CalibrationCancelled("cancelled")
            try:
                payload = self._responses.get(timeout=0.1)
            except queue.Empty:
                continue

            response_type = str(payload.get("response", ""))
            if response_type == "__cancel__":
                raise CalibrationCancelled("cancelled")
            if response_type not in allowed_responses:
                self.task_registry.record_status(
                    self.task_id,
                    "invalid_response",
                    f"当前步骤不接受操作：{response_type}",
                )
                continue

            if clear_prompt:
                self.task_registry.clear_prompt(self.task_id)
            return payload
