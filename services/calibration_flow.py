"""
Interactive calibration and test flows (CLI/desktop sequences).
"""
from __future__ import annotations

import sys
from pathlib import Path
from time import sleep as default_sleep
from typing import Callable, Optional

from services.calibration_config import (
    COPY_LINK_COUNTDOWN_SECONDS,
    OPEN_TABS_CLICKS,
    TOTAL_CALIBRATION_STEPS,
    WINDOW_ACTIVATION_WAIT_SECONDS,
    PointLike,
    _build_click_area,
    _working_config,
    get_coordinates_path,
    load_coordinates_config,
    load_required_coordinates_config,
    save_coordinates_config,
)

LogFn = Callable[[str], None]
ProgressFn = Callable[[int, int, str], None]
AskPositionFn = Callable[[str], Optional[PointLike]]
AskIntegerFn = Callable[[str, int], Optional[int]]
AskTextFn = Callable[[str], Optional[str]]
ConfirmFn = Callable[[str], bool]
ClickFn = Callable[[int, int], None]
ScrollFn = Callable[[int], None]
SleepFn = Callable[[float], None]
MoveToFn = Callable[[int, int, float], None]
ClickOptionalFn = Callable[..., None]
GetCurrentPositionFn = Callable[[], PointLike]


def _emit_progress(progress: Optional[ProgressFn], step: int, message: str) -> None:
    if progress:
        progress(step, TOTAL_CALIBRATION_STEPS, message)


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
    """Run the shared calibration sequence for interactive calibration flows."""
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
        log("提示：可以在桌面应用的校准页面中运行校准测试")
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
