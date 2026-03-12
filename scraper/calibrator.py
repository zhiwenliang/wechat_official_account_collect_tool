"""
坐标校准工具
用于记录微信窗口中关键按钮的坐标位置
"""
import pyautogui

from services.calibration_service import (
    run_calibration_flow,
    run_calibration_test_flow,
)


def get_mouse_position():
    """获取当前鼠标位置"""
    return pyautogui.position()


def calibrate():
    """交互式坐标校准"""
    def ask_position(prompt):
        input(prompt)
        return get_mouse_position()

    run_calibration_flow(
        mode="cli",
        ask_position=ask_position,
        ask_text=input,
        log=print,
        click=pyautogui.click,
        scroll=pyautogui.scroll,
        get_current_position=get_mouse_position,
    )


def test_calibration():
    """测试校准结果"""
    return run_calibration_test_flow(
        mode="cli",
        log=print,
        move_to=pyautogui.moveTo,
        click=pyautogui.click,
        scroll=pyautogui.scroll,
        pause=input,
        confirm=lambda prompt: input(prompt).strip().lower() == "y",
    )


if __name__ == "__main__":
    calibrate()
