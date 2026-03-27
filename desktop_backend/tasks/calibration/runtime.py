from __future__ import annotations

import time


class DesktopCalibrationRuntime:
    def __init__(self) -> None:
        import pyautogui

        self._pyautogui = pyautogui

    def get_current_position(self):
        return self._pyautogui.position()

    def click(self, x: int, y: int) -> None:
        self._pyautogui.click(x, y)

    def scroll(self, amount: int) -> None:
        self._pyautogui.scroll(amount)

    def move_to(self, x: int, y: int, duration: float) -> None:
        self._pyautogui.moveTo(x, y, duration)

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def default_calibration_runtime_factory():
    return DesktopCalibrationRuntime()
