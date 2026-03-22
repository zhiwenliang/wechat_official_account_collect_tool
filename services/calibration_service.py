"""
Shared calibration helpers for CLI and GUI flows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from time import sleep as default_sleep
from typing import Callable, Optional, Protocol

from utils.runtime_env import resolve_runtime_path

COORDINATES_RELATIVE_PATH = Path("config") / "coordinates.json"
COPY_LINK_COUNTDOWN_SECONDS = 10
OPEN_TABS_CLICKS = 20
TOTAL_CALIBRATION_STEPS = 8
WINDOW_ACTIVATION_WAIT_SECONDS = 0.2


class PointLike(Protocol):
    x: int
    y: int


LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int, str], None]
AskPositionFn = Callable[[str], Optional[PointLike]]
AskIntegerFn = Callable[[str, int], Optional[int]]
AskTextFn = Callable[[str], Optional[str]]
ConfirmFn = Callable[[str], bool]
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
StopCheckerFn = Callable[[], bool]


def get_coordinates_path() -> Path:
    """Return the writable coordinates config path."""
    return resolve_runtime_path(COORDINATES_RELATIVE_PATH)


def create_default_coordinates_config() -> dict:
    """Return the default coordinates config structure."""
    return {
        "windows": {
            "article_list": {
                "article_click_area": {"x": 0, "y": 0, "description": "文章点击位置"},
                "row_height": 0,
                "scroll_amount": 3,
                "visible_articles": 5,
            },
            "browser": {
                "more_button": {"x": 0, "y": 0, "description": "更多按钮"},
                "copy_link_menu": {"x": 0, "y": 0, "description": "复制链接菜单"},
                "first_tab": {"x": 0, "y": 0, "description": "第一个标签"},
                "close_tab_button": {"x": 0, "y": 0, "description": "关闭标签按钮"},
            },
        },
        "timing": {
            "click_interval": 0.3,
            "page_load_wait": 10.0,
            "menu_open_wait": 0.5,
        },
        "collection": {
            "max_articles": 1000,
        },
    }


def load_coordinates_config(create_if_missing: bool = False) -> dict:
    """Load the coordinates config from the repository path."""
    path = get_coordinates_path()
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    config = create_default_coordinates_config()
    if create_if_missing:
        save_coordinates_config(config)
    return config


def load_required_coordinates_config() -> dict:
    """Load coordinates config or raise if calibration has not been completed yet."""
    path = get_coordinates_path()
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}\n请先运行: python main.py calibrate")
    return load_coordinates_config()


def save_coordinates_config(config: dict) -> Path:
    """Persist the coordinates config to the repository path."""
    path = get_coordinates_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
    return path


def _emit_progress(progress: Optional[ProgressFn], step: int, message: str) -> None:
    if progress:
        progress(step, TOTAL_CALIBRATION_STEPS, message)


def _build_click_area(config: dict, pos_bottom: PointLike, row_height: int) -> int:
    click_y = pos_bottom.y - row_height // 2
    config["windows"]["article_list"]["article_click_area"] = {
        "x": pos_bottom.x,
        "y": click_y,
        "description": "文章点击位置（自动计算）",
    }
    config["windows"]["article_list"]["row_height"] = row_height
    return click_y


def _requires_window_activation() -> bool:
    """Return whether the current platform needs a focus-activation click."""
    return sys.platform == "darwin"


def _click_with_activation(
    click: ClickOptionalFn,
    sleep: SleepFn,
    x: int,
    y: int,
    *,
    activate_first: bool,
) -> None:
    """Click a target, optionally sending a first click to activate the window."""
    if activate_first:
        click(x, y)
        sleep(WINDOW_ACTIVATION_WAIT_SECONDS)
    click(x, y)


def _working_config(config: Optional[dict] = None) -> dict:
    """Return a mutable calibration config for GUI item updates."""
    return config if config is not None else load_coordinates_config(create_if_missing=False)


def _point_dict(point: PointLike, description: str) -> dict:
    """Convert a point-like object into the stored config shape."""
    return {
        "x": int(point.x),
        "y": int(point.y),
        "description": description,
    }


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


def calibrate_article_click_area(
    *,
    first_top: PointLike,
    second_top: PointLike,
    first_bottom: PointLike,
    config: Optional[dict] = None,
) -> dict:
    """Save article click area and row height from three sampled positions."""
    working_config = _working_config(config)
    row_height = abs(second_top.y - first_top.y)
    click_y = _build_click_area(working_config, first_bottom, row_height)
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "row_height": row_height,
        "click_area": {
            "x": int(first_bottom.x),
            "y": int(click_y),
        },
    }


def calibrate_scroll_amount(
    *,
    before_scroll: PointLike,
    after_scroll: PointLike,
    config: Optional[dict] = None,
) -> dict:
    """Save the scroll amount derived from the current row height."""
    working_config = _working_config(config)
    row_height = int(working_config["windows"]["article_list"].get("row_height") or 0)
    if row_height <= 0:
        raise ValueError("请先完成“文章点击位置”校准，才能计算滚动单位")

    pixels_per_unit = abs(after_scroll.y - before_scroll.y)
    scroll_amount = round(row_height / pixels_per_unit) if pixels_per_unit > 0 else 3
    working_config["windows"]["article_list"]["scroll_amount"] = scroll_amount
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "scroll_amount": scroll_amount,
        "pixels_per_unit": pixels_per_unit,
        "row_height": row_height,
    }


def set_visible_articles(*, visible_count: int, config: Optional[dict] = None) -> dict:
    """Persist the visible article count."""
    working_config = _working_config(config)
    working_config["windows"]["article_list"]["visible_articles"] = int(visible_count)
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "visible_count": int(visible_count),
    }


def calibrate_more_button(*, position: PointLike, config: Optional[dict] = None) -> dict:
    """Save the browser more-button position."""
    working_config = _working_config(config)
    working_config["windows"]["browser"]["more_button"] = _point_dict(position, "右上角更多按钮")
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "position": working_config["windows"]["browser"]["more_button"],
    }


def calibrate_copy_link_menu(*, position: PointLike, config: Optional[dict] = None) -> dict:
    """Save the copy-link menu position."""
    working_config = _working_config(config)
    working_config["windows"]["browser"]["copy_link_menu"] = _point_dict(position, "复制链接菜单项")
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "position": working_config["windows"]["browser"]["copy_link_menu"],
    }


def calibrate_tab_management(
    *,
    first_tab: PointLike,
    close_button: PointLike,
    config: Optional[dict] = None,
) -> dict:
    """Save the tab-management positions in one operation."""
    working_config = _working_config(config)
    working_config["windows"]["browser"]["first_tab"] = _point_dict(first_tab, "第一个标签位置")
    working_config["windows"]["browser"]["close_tab_button"] = _point_dict(close_button, "标签关闭按钮")
    path = save_coordinates_config(working_config)
    return {
        "path": path,
        "first_tab": working_config["windows"]["browser"]["first_tab"],
        "close_button": working_config["windows"]["browser"]["close_tab_button"],
    }


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


def open_calibration_article_tab(
    *,
    click: ClickFn,
    sleep: SleepFn = default_sleep,
    config: Optional[dict] = None,
) -> None:
    """Open one article tab using the current click target and macOS activation rules."""
    working_config = _working_config(config)
    click_area = working_config["windows"]["article_list"].get("article_click_area") or {}
    click_x = click_area.get("x")
    click_y = click_area.get("y")
    if click_x is None or click_y is None:
        raise ValueError("请先完成“文章点击位置”校准")

    _click_with_activation(
        click,
        sleep,
        int(click_x),
        int(click_y),
        activate_first=_requires_window_activation(),
    )


def run_calibration_flow(
    *,
    mode: str,
    ask_position: AskPositionFn,
    ask_integer: Optional[AskIntegerFn] = None,
    ask_text: Optional[AskTextFn] = None,
    log: LogFn = print,
    progress: Optional[ProgressFn] = None,
    sleep: SleepFn = default_sleep,
    click: ClickFn,
    scroll: ScrollFn,
    get_current_position: GetCurrentPositionFn,
) -> Optional[Path]:
    """Run the shared calibration sequence for CLI or GUI."""
    config = load_coordinates_config(create_if_missing=False)
    existing_config = get_coordinates_path().exists()

    if mode == "cli":
        if ask_text is None:
            raise ValueError("ask_text is required for CLI calibration")
        log("=== 微信公众号文章采集 - 坐标校准工具 ===\n")
        log("请按照提示将鼠标移动到指定位置，然后按回车键记录坐标")
        log("注意：校准后请勿移动窗口位置和大小\n")
        if not existing_config:
            log("配置文件不存在，正在创建默认配置...\n")
        log("--- 公众号窗口 ---")
        log("准备：请先点击【文章分组】按钮，并滚动到页面最顶部\n")
        log("--- 测量文章行高 ---")
        pos1 = ask_position("1. 将鼠标移动到【任意一篇文章的顶部】，按回车...")
        if pos1 is None:
            return None
        log(f"   文章顶部: ({pos1.x}, {pos1.y})")
        pos2 = ask_position("   将鼠标移动到【下一篇文章的顶部】，按回车...")
        if pos2 is None:
            return None
        log(f"   下一篇顶部: ({pos2.x}, {pos2.y})")
    else:
        log("开始坐标校准...")
        _emit_progress(progress, 1, "测量文章行高")
        pos1 = ask_position("请将鼠标移动到【任意一篇文章的顶部】，点击记录后继续")
        if pos1 is None:
            return None
        pos2 = ask_position("请将鼠标移动到【下一篇文章的顶部】，点击记录后继续")
        if pos2 is None:
            return None

    row_height = abs(pos2.y - pos1.y)
    if mode == "cli":
        log(f"   已计算行高: {row_height} 像素\n")
        log("--- 获取第一篇文章底部 ---")
        pos_bottom = ask_position("2. 将鼠标移动到【第一篇文章的底部】，按回车...")
        if pos_bottom is None:
            return None
        log(f"   第一篇底部: ({pos_bottom.x}, {pos_bottom.y})")
    else:
        log(f"已计算行高: {row_height} 像素")
        _emit_progress(progress, 2, "获取文章底部位置")
        pos_bottom = ask_position("请将鼠标移动到【第一篇文章的底部】，点击记录后继续")
        if pos_bottom is None:
            return None

    click_y = _build_click_area(config, pos_bottom, row_height)

    if mode == "cli":
        log("--- 测试滚动单位 ---")
        log("将测量1个滚动单位对应多少像素\n")
        log("操作说明：")
        log("1. 将鼠标移动到文章列表区域内的参考点（如某篇文章的标题开头）")
        log("2. 记录参考点位置，然后在该位置执行1单位滚动")
        log("3. 滚动后，再次定位到同一参考点")
        log("4. 计算位置差值即为1单位对应的像素\n")
        pos_before = ask_position("将鼠标移动到文章列表区域内的参考点，按回车...")
        if pos_before is None:
            return None
        log(f"   初始位置: ({pos_before.x}, {pos_before.y})")
        log("   将执行1单位滚动...")
        sleep(0.5)
    else:
        _emit_progress(progress, 3, "测试滚动单位")
        pos_before = ask_position("将鼠标移动到文章列表区域内的参考点，点击记录后系统将自动滚动")
        if pos_before is None:
            return None

    scroll(-1)
    sleep(1)

    if mode == "cli":
        pos_after = ask_position("   将鼠标移动到同一参考点（滚动后），按回车...")
        if pos_after is None:
            return None
        log(f"   滚动后位置: ({pos_after.x}, {pos_after.y})")
    else:
        pos_after = ask_position("滚动完成后，将鼠标移动到同一参考点，点击记录")
        if pos_after is None:
            return None

    pixels_per_unit = abs(pos_after.y - pos_before.y)
    optimal_units = round(row_height / pixels_per_unit) if pixels_per_unit > 0 else 3
    if mode == "cli":
        log(f"\n   1个滚动单位 = {pixels_per_unit} 像素")
        log(f"   行高 = {row_height} 像素")
        log(f"   行高 {row_height} 像素 / {pixels_per_unit} 像素/单位 = {optimal_units} 单位")
        confirm = (ask_text(f"   建议使用 {optimal_units} 个滚动单位，是否接受？(y/n): ") or "").strip().lower()
        if confirm == "y":
            scroll_amount = optimal_units
        else:
            manual = (ask_text("   输入自定义滚动单位: ") or "").strip()
            scroll_amount = int(manual) if manual else optimal_units
        log(f"   已记录滚动单位: {scroll_amount}\n")
        log(f"   已计算点击位置: ({pos_bottom.x}, {click_y})\n")
        visible_count_text = (ask_text("3. 输入窗口可见文章数量（用于最后处理剩余文章，如5）: ") or "").strip()
        visible_count = int(visible_count_text) if visible_count_text else 5
        config["windows"]["article_list"]["visible_articles"] = visible_count
        log(f"   已记录: {visible_count} 篇\n")
        log("--- 微信内置浏览器窗口 ---")
    else:
        scroll_amount = optimal_units
        log(f"已记录滚动单位: {scroll_amount}")
        _emit_progress(progress, 4, "设置可见文章数")
        if ask_integer is None:
            raise ValueError("ask_integer is required for GUI calibration")
        visible_count = ask_integer(
            "请输入当前窗口中同时可见的文章数量（用于处理最后一屏文章）",
            5,
        )
        if visible_count is None:
            return None
        config["windows"]["article_list"]["visible_articles"] = visible_count
        log(f"已记录可见文章数: {visible_count}")

    config["windows"]["article_list"]["scroll_amount"] = scroll_amount

    if mode == "cli":
        more_btn = ask_position("4. 将鼠标移动到【右上角更多按钮】上，按回车...")
    else:
        _emit_progress(progress, 5, "定位更多按钮")
        more_btn = ask_position("请将鼠标移动到【右上角更多按钮】上，点击记录")
    if more_btn is None:
        return None
    config["windows"]["browser"]["more_button"] = {
        "x": more_btn.x,
        "y": more_btn.y,
        "description": "右上角更多按钮",
    }
    if mode == "cli":
        log(f"   已记录: ({more_btn.x}, {more_btn.y})\n")
        log("5. 获取【复制链接菜单项】位置")
        log("   准备：点击更多按钮后，窗口焦点会跳转")
        log("   操作：按回车后，10秒内完成以下步骤：")
        log("        1) 点击更多按钮")
        log("        2) 将鼠标移动到复制链接菜单项上")
        if ask_text("   准备好后按回车开始倒计时...") is None:
            return None
    else:
        _emit_progress(progress, 6, "定位复制链接菜单")
        if ask_position(
            "获取【复制链接菜单项】位置\n\n"
            f"确认(Enter)后，将开始 {COPY_LINK_COUNTDOWN_SECONDS} 秒倒计时。\n"
            "请在倒计时内完成：\n"
            "1) 点击右上角【更多】按钮打开菜单\n"
            "2) 将鼠标移动到【复制链接】菜单项上并保持不动\n\n"
            "倒计时结束后将自动记录当前鼠标位置。"
        ) is None:
            return None

    for i in range(COPY_LINK_COUNTDOWN_SECONDS, 0, -1):
        if mode == "cli":
            log(f"   {i}秒...")
        else:
            _emit_progress(progress, 6, f"复制链接菜单倒计时: {i} 秒")
        sleep(1)

    copy_menu = get_current_position()
    config["windows"]["browser"]["copy_link_menu"] = {
        "x": copy_menu.x,
        "y": copy_menu.y,
        "description": "复制链接菜单项",
    }
    if mode == "cli":
        log(f"   已记录: ({copy_menu.x}, {copy_menu.y})\n")
        log("--- 标签管理（防止浏览器崩溃）---")
        log("需要先打开20个标签以获取实际标签位置")
        if ask_text("6. 准备好后按回车，将自动点击文章20次...") is None:
            return None
        log("   自动点击中...")
    else:
        _emit_progress(progress, 7, "定位第一个标签")
        if ask_position(
            "标签管理准备\n\n"
            f"确认(Enter)后，程序将自动点击文章 {OPEN_TABS_CLICKS} 次以提前打开标签。\n"
            "请确保微信窗口已就绪，且不要移动鼠标/窗口。\n\n"
            "提示：如需中止，可将鼠标移到屏幕角落触发 pyautogui failsafe。"
        ) is None:
            return None
        log(f"开始自动点击文章 {OPEN_TABS_CLICKS} 次以打开标签...")

    click_area = config["windows"]["article_list"].get("article_click_area") or {}
    click_x = click_area.get("x")
    click_y = click_area.get("y")
    if click_x is None or click_y is None:
        raise RuntimeError("文章点击位置未校准，无法自动打开标签")

    needs_window_activation = _requires_window_activation()
    if needs_window_activation:
        log("检测到 macOS，将在每次点击前先激活公众号窗口。")

    for i in range(OPEN_TABS_CLICKS):
        _click_with_activation(
            click,
            sleep,
            click_x,
            click_y,
            activate_first=needs_window_activation,
        )
        if mode == "cli":
            log(f"   已点击 {i+1}/20")
        else:
            _emit_progress(progress, 7, f"自动打开标签: {i + 1}/{OPEN_TABS_CLICKS}")
        sleep(2)
    if mode == "cli":
        log("   ✓ 已打开20个标签\n")
        first_tab = ask_position("7. 将鼠标移动到【第一个标签】上，按回车...")
    else:
        log("已打开标签，准备记录第一个标签位置")
        first_tab = ask_position("将鼠标移动到【第一个标签】上，确认(Enter)后记录位置")
    if first_tab is None:
        return None
    config["windows"]["browser"]["first_tab"] = {
        "x": first_tab.x,
        "y": first_tab.y,
        "description": "第一个标签位置",
    }
    if mode == "cli":
        log(f"   已记录: ({first_tab.x}, {first_tab.y})\n")
        close_btn = ask_position("8. 将鼠标移动到【标签关闭按钮】上，按回车...")
    else:
        _emit_progress(progress, 8, "定位关闭按钮")
        close_btn = ask_position("请将鼠标移动到【标签关闭按钮】上，点击记录")
    if close_btn is None:
        return None
    config["windows"]["browser"]["close_tab_button"] = {
        "x": close_btn.x,
        "y": close_btn.y,
        "description": "标签关闭按钮",
    }
    if mode == "cli":
        log(f"   已记录: ({close_btn.x}, {close_btn.y})\n")

    path = save_coordinates_config(config)
    if mode == "cli":
        log(f"✓ 坐标配置已保存到: {path}")
        log("\n校准完成！")
        log("提示：可以运行 'python main.py test' 测试校准结果")
    else:
        log(f"坐标配置已保存到: {path}")
    return path


def run_calibration_test_flow(
    *,
    mode: str,
    log: LogFn = print,
    move_to: MoveToFn,
    click: ClickOptionalFn,
    scroll: ScrollFn,
    sleep: SleepFn = default_sleep,
    pause: Optional[AskTextFn] = None,
    confirm: Optional[ConfirmFn] = None,
) -> Optional[bool]:
    """Run the shared calibration test sequence."""
    if pause is None or confirm is None:
        raise ValueError("pause and confirm are required for calibration test flow")

    config = load_required_coordinates_config()
    click_area = config["windows"]["article_list"]["article_click_area"]
    more_btn = config["windows"]["browser"]["more_button"]
    copy_menu = config["windows"]["browser"]["copy_link_menu"]
    first_tab = config["windows"]["browser"]["first_tab"]
    close_btn = config["windows"]["browser"]["close_tab_button"]
    needs_window_activation = _requires_window_activation()

    heading = "\n=== 测试校准结果 ===\n" if mode == "cli" else "=== 开始测试坐标 ===\n"
    log(heading)

    log("--- 测试文章点击位置 ---")
    log(f"将移动鼠标到文章点击位置: ({click_area['x']}, {click_area['y']})")
    if pause("按回车开始...") is None:
        return None
    move_to(click_area["x"], click_area["y"], 1)
    if not confirm("鼠标位置是否在第一篇文章中间？"):
        log("  ⚠ 位置不准确，建议重新校准")
        return False
    log("  ✓ 位置正确\n")

    log("--- 测试滚动功能 ---")
    scroll_amount = config["windows"]["article_list"]["scroll_amount"]
    log(f"将滚动 {scroll_amount} 像素")
    if pause("按回车开始...") is None:
        return None
    move_to(click_area["x"], click_area["y"], 1)
    scroll(-scroll_amount)
    if not confirm("滚动距离是否正好一行？"):
        log("  ⚠ 滚动距离不准确，建议重新校准")
        return False
    log("  ✓ 滚动正确\n")

    log("--- 测试更多按钮位置 ---")
    log(f"将移动鼠标到更多按钮: ({more_btn['x']}, {more_btn['y']})")
    if pause("按回车开始...") is None:
        return None
    move_to(more_btn["x"], more_btn["y"], 1)
    if not confirm("鼠标位置是否在更多按钮上？"):
        log("  ⚠ 位置不准确，建议重新校准")
        return False
    log("  ✓ 位置正确\n")

    log("--- 测试复制链接菜单位置 ---")
    log(f"将测试复制链接菜单位置: ({copy_menu['x']}, {copy_menu['y']})")
    log("操作：先点击更多按钮，然后移动鼠标到复制链接菜单项")
    if pause("按回车开始...") is None:
        return None
    move_to(more_btn["x"], more_btn["y"], 1)
    _click_with_activation(
        click,
        sleep,
        more_btn["x"],
        more_btn["y"],
        activate_first=needs_window_activation,
    )
    sleep(0.5)
    move_to(copy_menu["x"], copy_menu["y"], 1)
    if not confirm("鼠标位置是否在复制链接菜单项上？"):
        log("  ⚠ 位置不准确，建议重新校准")
        return False
    log("  ✓ 位置正确\n")

    log("--- 测试标签关闭功能 ---")
    log("将测试标签关闭功能（先打开3个标签，然后测试关闭）")
    if pause("按回车开始...") is None:
        return None
    log("  打开3个测试标签...")
    for i in range(3):
        _click_with_activation(
            click,
            sleep,
            click_area["x"],
            click_area["y"],
            activate_first=needs_window_activation,
        )
        log(f"  已打开 {i+1}/3")
        sleep(2)

    log(f"\n  测试点击第一个标签: ({first_tab['x']}, {first_tab['y']})")
    move_to(first_tab["x"], first_tab["y"], 1)
    if not confirm("鼠标是否在第一个标签上？"):
        log("  ⚠ 位置不准确，建议重新校准")
        return False

    click(first_tab["x"], first_tab["y"])
    sleep(0.5)

    log(f"\n  测试点击关闭按钮: ({close_btn['x']}, {close_btn['y']})")
    move_to(close_btn["x"], close_btn["y"], 1)
    if not confirm("鼠标是否在关闭按钮上？"):
        log("  ⚠ 位置不准确，建议重新校准")
        return False

    for _ in range(2):
        click(close_btn["x"], close_btn["y"])
        sleep(0.3)

    if not confirm("标签是否正确关闭？"):
        log("  ⚠ 标签关闭功能异常，建议重新校准")
        return False

    log("  ✓ 标签关闭正确\n")
    log("=" * 60)
    log("✓ 所有测试通过！可以开始采集了。")
    return True
