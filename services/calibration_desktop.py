"""
Desktop calibration prompts and per-action handlers.
"""
from __future__ import annotations

from time import sleep as default_sleep
from typing import Callable, Optional

from services.calibration_config import (
    COPY_LINK_COUNTDOWN_SECONDS,
    OPEN_TABS_CLICKS,
    PointLike,
    calibrate_article_click_area,
    calibrate_copy_link_menu,
    calibrate_more_button,
    calibrate_scroll_amount,
    calibrate_tab_management,
    load_coordinates_config,
    set_visible_articles,
)
from services.calibration_flow import (
    open_calibration_article_tab,
    run_calibration_test_flow,
)

LogFn = Callable[[str], None]
StopCheckerFn = Callable[[], bool]
DesktopRequestPositionFn = Callable[[str, str, str], Optional[PointLike]]
DesktopRequestAckFn = Callable[[str, str, str], Optional[bool]]
DesktopRequestIntegerFn = Callable[[str, str, str, int, int], Optional[int]]
DesktopRequestConfirmFn = Callable[[str, str, str, str, str], Optional[bool]]
GetCurrentPositionFn = Callable[[], PointLike]
ClickFn = Callable[[int, int], None]
ScrollFn = Callable[[int], None]
SleepFn = Callable[[float], None]
MoveToFn = Callable[[int, int, float], None]
ClickOptionalFn = Callable[..., None]


class CalibrationCancelled(Exception):
    """Raised when an interactive calibration task is cancelled."""


def _ensure_not_cancelled(stop_checker: Optional[StopCheckerFn]) -> None:
    if stop_checker and stop_checker():
        raise CalibrationCancelled("cancelled")


def _require_desktop_position(
    request_position: DesktopRequestPositionFn,
    *,
    step: str,
    title: str,
    message: str,
    stop_checker: Optional[StopCheckerFn] = None,
) -> PointLike:
    _ensure_not_cancelled(stop_checker)
    position = request_position(step, title, message)
    if position is None:
        raise CalibrationCancelled("cancelled")
    _ensure_not_cancelled(stop_checker)
    return position


def _require_desktop_ack(
    request_ack: DesktopRequestAckFn,
    *,
    step: str,
    title: str,
    message: str,
    stop_checker: Optional[StopCheckerFn] = None,
) -> bool:
    _ensure_not_cancelled(stop_checker)
    acknowledged = request_ack(step, title, message)
    if acknowledged is None:
        raise CalibrationCancelled("cancelled")
    _ensure_not_cancelled(stop_checker)
    return bool(acknowledged)


def _require_desktop_integer(
    request_integer: DesktopRequestIntegerFn,
    *,
    step: str,
    title: str,
    message: str,
    default_value: int,
    min_value: int = 1,
    stop_checker: Optional[StopCheckerFn] = None,
) -> int:
    _ensure_not_cancelled(stop_checker)
    value = request_integer(step, title, message, default_value, min_value)
    if value is None:
        raise CalibrationCancelled("cancelled")
    _ensure_not_cancelled(stop_checker)
    return int(value)


def _require_desktop_confirm(
    request_confirm: DesktopRequestConfirmFn,
    *,
    step: str,
    title: str,
    message: str,
    confirm_label: str,
    reject_label: str,
    stop_checker: Optional[StopCheckerFn] = None,
) -> bool:
    _ensure_not_cancelled(stop_checker)
    accepted = request_confirm(step, title, message, confirm_label, reject_label)
    if accepted is None:
        raise CalibrationCancelled("cancelled")
    _ensure_not_cancelled(stop_checker)
    return bool(accepted)


def run_desktop_calibration_action(
    *,
    action: str,
    request_position: DesktopRequestPositionFn,
    request_ack: DesktopRequestAckFn,
    request_integer: DesktopRequestIntegerFn,
    request_confirm: DesktopRequestConfirmFn,
    get_current_position: GetCurrentPositionFn,
    click: ClickFn,
    scroll: ScrollFn,
    move_to: MoveToFn,
    sleep: SleepFn = default_sleep,
    log: LogFn = print,
    status: LogFn = print,
    stop_checker: Optional[StopCheckerFn] = None,
):
    """Run one desktop-friendly calibration action using prompt callbacks."""
    if action == "article_click_area":
        log("开始校准：文章点击位置")
        first_top = _require_desktop_position(
            request_position,
            step="article_click_area.first_top",
            title="文章点击位置",
            message="步骤 1/3：请将鼠标移动到【任意一篇文章的顶部】。",
            stop_checker=stop_checker,
        )
        second_top = _require_desktop_position(
            request_position,
            step="article_click_area.second_top",
            title="文章点击位置",
            message="步骤 2/3：请将鼠标移动到【下一篇文章的顶部】。",
            stop_checker=stop_checker,
        )
        first_bottom = _require_desktop_position(
            request_position,
            step="article_click_area.first_bottom",
            title="文章点击位置",
            message="步骤 3/3：请将鼠标移动到【第一篇文章的底部】。",
            stop_checker=stop_checker,
        )
        result = calibrate_article_click_area(
            first_top=first_top,
            second_top=second_top,
            first_bottom=first_bottom,
        )
        click_area = result["click_area"]
        log(f"文章点击位置已保存：({click_area['x']}, {click_area['y']}), 行高 {result['row_height']} 像素。")
        return result

    if action == "scroll_amount":
        log("开始校准：滚动单位")
        before_scroll = _require_desktop_position(
            request_position,
            step="scroll_amount.before_scroll",
            title="滚动单位",
            message="步骤 1/2：请将鼠标移动到文章列表中的某个参考点，记录后程序会自动滚动 1 单位。",
            stop_checker=stop_checker,
        )
        status("滚动单位：正在自动滚动 1 单位，请准备记录滚动后的同一参考点。")
        scroll(-1)
        sleep(1)
        after_scroll = _require_desktop_position(
            request_position,
            step="scroll_amount.after_scroll",
            title="滚动单位",
            message="步骤 2/2：请将鼠标移动到【滚动后的同一参考点】。",
            stop_checker=stop_checker,
        )
        result = calibrate_scroll_amount(
            before_scroll=before_scroll,
            after_scroll=after_scroll,
        )
        log(f"滚动单位已保存：{result['scroll_amount']}（参考像素差 {result['pixels_per_unit']}）。")
        return result

    if action == "visible_articles":
        log("开始设置：可见文章数")
        config = load_coordinates_config(create_if_missing=False)
        default_value = int(config["windows"]["article_list"].get("visible_articles") or 5)
        visible_count = _require_desktop_integer(
            request_integer,
            step="visible_articles.value",
            title="可见文章数",
            message="请输入当前窗口中同时可见的文章数量。",
            default_value=default_value,
            min_value=1,
            stop_checker=stop_checker,
        )
        result = set_visible_articles(visible_count=visible_count)
        log(f"可见文章数已保存：{result['visible_count']}。")
        return result

    if action == "more_button":
        log("开始校准：更多按钮")
        position = _require_desktop_position(
            request_position,
            step="more_button.position",
            title="更多按钮",
            message="请将鼠标移动到微信内置浏览器右上角【更多】按钮。",
            stop_checker=stop_checker,
        )
        result = calibrate_more_button(position=position)
        saved = result["position"]
        log(f"更多按钮已保存：({saved['x']}, {saved['y']})。")
        return result

    if action == "copy_link_menu":
        log("开始校准：复制链接菜单")
        _require_desktop_ack(
            request_ack,
            step="copy_link_menu.prepare",
            title="复制链接菜单",
            message=(
                "确认后将开始倒计时。\n\n"
                "请在倒计时内完成：\n"
                "1. 点击右上角【更多】按钮打开菜单\n"
                "2. 将鼠标移动到【复制链接】菜单项上并保持不动"
            ),
            stop_checker=stop_checker,
        )
        for seconds_left in range(COPY_LINK_COUNTDOWN_SECONDS, 0, -1):
            _ensure_not_cancelled(stop_checker)
            status(f"复制链接菜单：倒计时 {seconds_left} 秒，请在微信中打开菜单并将鼠标停在目标项上。")
            sleep(1)
        result = calibrate_copy_link_menu(position=get_current_position())
        saved = result["position"]
        log(f"复制链接菜单已保存：({saved['x']}, {saved['y']})。")
        return result

    if action == "tab_management":
        log("开始校准：标签管理")
        config = load_coordinates_config(create_if_missing=False)
        click_area = config["windows"]["article_list"].get("article_click_area") or {}
        if int(click_area.get("x") or 0) <= 0 or int(click_area.get("y") or 0) <= 0:
            raise ValueError("请先完成“文章点击位置”校准，再进行标签管理校准。")

        _require_desktop_ack(
            request_ack,
            step="tab_management.prepare",
            title="标签管理",
            message=(
                "确认后，程序会自动点击文章 20 次以打开标签。\n\n"
                "请确保微信窗口已就绪，且不要移动鼠标或窗口。"
            ),
            stop_checker=stop_checker,
        )

        for index in range(OPEN_TABS_CLICKS):
            _ensure_not_cancelled(stop_checker)
            status(f"标签管理：正在自动打开标签 {index + 1}/{OPEN_TABS_CLICKS}...")
            open_calibration_article_tab(click=click, sleep=sleep)
            sleep(2)

        first_tab = _require_desktop_position(
            request_position,
            step="tab_management.first_tab",
            title="标签管理",
            message="步骤 1/2：请将鼠标移动到【第一个标签】上。",
            stop_checker=stop_checker,
        )
        close_button = _require_desktop_position(
            request_position,
            step="tab_management.close_button",
            title="标签管理",
            message="步骤 2/2：请将鼠标移动到【标签关闭按钮】上。",
            stop_checker=stop_checker,
        )
        result = calibrate_tab_management(first_tab=first_tab, close_button=close_button)
        saved_first = result["first_tab"]
        saved_close = result["close_button"]
        log(
            "标签管理已保存："
            f"第一个标签 ({saved_first['x']}, {saved_first['y']}), "
            f"关闭按钮 ({saved_close['x']}, {saved_close['y']})。"
        )
        return result

    if action == "test":
        log("开始执行：校准测试")
        pause_steps = [
            ("test.article_click_area.prepare", "校准测试"),
            ("test.scroll_amount.prepare", "校准测试"),
            ("test.more_button.prepare", "校准测试"),
            ("test.copy_link_menu.prepare", "校准测试"),
            ("test.tab_management.prepare", "校准测试"),
        ]
        confirm_steps = [
            ("test.article_click_area", "校准测试", "是", "否"),
            ("test.scroll_amount", "校准测试", "是", "否"),
            ("test.more_button", "校准测试", "是", "否"),
            ("test.copy_link_menu", "校准测试", "是", "否"),
            ("test.tab_management.first_tab", "校准测试", "是", "否"),
            ("test.tab_management.close_button", "校准测试", "是", "否"),
            ("test.tab_management.closed", "校准测试", "是", "否"),
        ]
        pause_index = 0
        confirm_index = 0

        def pause_callback(prompt: str) -> str:
            nonlocal pause_index
            step, title = pause_steps[pause_index] if pause_index < len(pause_steps) else (f"test.pause.{pause_index}", "校准测试")
            pause_index += 1
            _require_desktop_ack(
                request_ack,
                step=step,
                title=title,
                message=prompt,
                stop_checker=stop_checker,
            )
            return ""

        def confirm_callback(prompt: str) -> bool:
            nonlocal confirm_index
            if confirm_index < len(confirm_steps):
                step, title, confirm_label, reject_label = confirm_steps[confirm_index]
            else:
                step, title, confirm_label, reject_label = (f"test.confirm.{confirm_index}", "校准测试", "是", "否")
            confirm_index += 1
            return _require_desktop_confirm(
                request_confirm,
                step=step,
                title=title,
                message=prompt,
                confirm_label=confirm_label,
                reject_label=reject_label,
                stop_checker=stop_checker,
            )

        return run_calibration_test_flow(
            mode="desktop",
            log=log,
            move_to=move_to,
            click=click,
            scroll=scroll,
            sleep=sleep,
            pause=pause_callback,
            confirm=confirm_callback,
        )

    raise ValueError(f"unsupported calibration action: {action}")
