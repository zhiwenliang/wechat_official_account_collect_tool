"""
Main entry point for the GUI application.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from utils.runtime_env import configure_runtime_environment, resolve_runtime_path

configure_runtime_environment()


def _get_startup_log_path() -> Path:
    return resolve_runtime_path("wechat-scraper-startup.log")


def _report_startup_failure(exc: Exception) -> None:
    log_path = _get_startup_log_path()
    trace_text = traceback.format_exc()

    try:
        log_path.write_text(trace_text, encoding="utf-8")
    except Exception:
        pass

    message = (
        "程序启动失败，错误详情已写入:\n"
        f"{log_path}\n\n"
        f"{exc}"
    )

    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("启动失败", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)
        print(trace_text, file=sys.stderr)


def main() -> None:
    """Launch the GUI application."""
    try:
        from gui.app import WeChatScraperGUI

        app = WeChatScraperGUI()
        app.run()
    except Exception as exc:
        _report_startup_failure(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
