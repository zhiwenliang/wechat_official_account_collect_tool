from __future__ import annotations

from services.calibration_service import (
    get_coordinates_path,
    load_coordinates_config,
)


def _is_position_calibrated(pos: dict) -> bool:
    return bool(pos.get("x") or pos.get("y"))


def get_calibration_status_handler() -> dict[str, bool]:
    if not get_coordinates_path().exists():
        return {
            "article_click_area": False,
            "scroll_amount": False,
            "visible_articles": False,
            "more_button": False,
            "copy_link_menu": False,
            "tab_management": False,
        }
    config = load_coordinates_config()
    article_list = config.get("windows", {}).get("article_list", {})
    browser = config.get("windows", {}).get("browser", {})
    click_area = article_list.get("article_click_area", {})
    more_btn = browser.get("more_button", {})
    copy_menu = browser.get("copy_link_menu", {})
    first_tab = browser.get("first_tab", {})
    return {
        "article_click_area": _is_position_calibrated(click_area),
        "scroll_amount": int(article_list.get("row_height", 0)) > 0,
        "visible_articles": int(article_list.get("visible_articles", 0)) > 0,
        "more_button": _is_position_calibrated(more_btn),
        "copy_link_menu": _is_position_calibrated(copy_menu),
        "tab_management": _is_position_calibrated(first_tab),
    }
