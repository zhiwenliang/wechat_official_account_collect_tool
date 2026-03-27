"""
Coordinates config path, defaults, persistence, and calibration mutations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Protocol

COORDINATES_RELATIVE_PATH = Path("config") / "coordinates.json"
COPY_LINK_COUNTDOWN_SECONDS = 10
OPEN_TABS_CLICKS = 20
TOTAL_CALIBRATION_STEPS = 8
WINDOW_ACTIVATION_WAIT_SECONDS = 0.2


class PointLike(Protocol):
    x: int
    y: int


def get_coordinates_path() -> Path:
    """Return the writable coordinates config path."""
    import services.calibration_service as _calibration_facade

    return _calibration_facade.resolve_runtime_path(COORDINATES_RELATIVE_PATH)


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
        raise FileNotFoundError(f"配置文件不存在: {path}\n请先在桌面应用中完成坐标校准")
    return load_coordinates_config()


def save_coordinates_config(config: dict) -> Path:
    """Persist the coordinates config to the repository path."""
    path = get_coordinates_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
    return path


def _build_click_area(config: dict, pos_bottom: PointLike, row_height: int) -> int:
    click_y = pos_bottom.y - row_height // 2
    config["windows"]["article_list"]["article_click_area"] = {
        "x": pos_bottom.x,
        "y": click_y,
        "description": "文章点击位置（自动计算）",
    }
    config["windows"]["article_list"]["row_height"] = row_height
    return click_y


def _working_config(config: Optional[dict] = None) -> dict:
    """Return a mutable calibration config for desktop item updates."""
    return config if config is not None else load_coordinates_config(create_if_missing=False)


def _point_dict(point: PointLike, description: str) -> dict:
    """Convert a point-like object into the stored config shape."""
    return {
        "x": int(point.x),
        "y": int(point.y),
        "description": description,
    }


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
