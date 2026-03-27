"""
Shared calibration helpers for desktop-facing flows.

Compatibility facade over ``calibration_config``, ``calibration_desktop``, and
``calibration_flow``.
"""
from __future__ import annotations

from utils.runtime_env import resolve_runtime_path

from services.calibration_config import (
    COORDINATES_RELATIVE_PATH,
    COPY_LINK_COUNTDOWN_SECONDS,
    OPEN_TABS_CLICKS,
    TOTAL_CALIBRATION_STEPS,
    WINDOW_ACTIVATION_WAIT_SECONDS,
    PointLike,
    calibrate_article_click_area,
    calibrate_copy_link_menu,
    calibrate_more_button,
    calibrate_scroll_amount,
    calibrate_tab_management,
    create_default_coordinates_config,
    get_coordinates_path,
    load_coordinates_config,
    load_required_coordinates_config,
    save_coordinates_config,
    set_visible_articles,
)
from services.calibration_desktop import (
    CalibrationCancelled,
    ClickFn,
    DesktopRequestAckFn,
    DesktopRequestConfirmFn,
    DesktopRequestIntegerFn,
    DesktopRequestPositionFn,
    GetCurrentPositionFn,
    LogFn,
    MoveToFn,
    ScrollFn,
    SleepFn,
    StopCheckerFn,
    run_desktop_calibration_action,
)
from services.calibration_flow import (
    AskIntegerFn,
    AskPositionFn,
    AskTextFn,
    ClickOptionalFn,
    ConfirmFn,
    ProgressFn,
    open_calibration_article_tab,
    run_calibration_flow,
    run_calibration_test_flow,
)

__all__ = [
    "COORDINATES_RELATIVE_PATH",
    "COPY_LINK_COUNTDOWN_SECONDS",
    "OPEN_TABS_CLICKS",
    "TOTAL_CALIBRATION_STEPS",
    "WINDOW_ACTIVATION_WAIT_SECONDS",
    "PointLike",
    "LogFn",
    "ProgressFn",
    "AskPositionFn",
    "AskIntegerFn",
    "AskTextFn",
    "ConfirmFn",
    "DesktopRequestPositionFn",
    "DesktopRequestAckFn",
    "DesktopRequestIntegerFn",
    "DesktopRequestConfirmFn",
    "GetCurrentPositionFn",
    "ClickFn",
    "ScrollFn",
    "SleepFn",
    "MoveToFn",
    "ClickOptionalFn",
    "StopCheckerFn",
    "CalibrationCancelled",
    "resolve_runtime_path",
    "get_coordinates_path",
    "create_default_coordinates_config",
    "load_coordinates_config",
    "load_required_coordinates_config",
    "save_coordinates_config",
    "calibrate_article_click_area",
    "calibrate_scroll_amount",
    "set_visible_articles",
    "calibrate_more_button",
    "calibrate_copy_link_menu",
    "calibrate_tab_management",
    "run_desktop_calibration_action",
    "open_calibration_article_tab",
    "run_calibration_flow",
    "run_calibration_test_flow",
]
