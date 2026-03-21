"""
Main GUI Application for WeChat Official Account Scraper
Provides a user-friendly interface for link collection and content scraping
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import threading
import webbrowser
import os
import time
from pathlib import Path
from datetime import datetime

from services.calibration_service import (
    COPY_LINK_COUNTDOWN_SECONDS,
    OPEN_TABS_CLICKS,
    calibrate_article_click_area,
    calibrate_copy_link_menu,
    calibrate_more_button,
    calibrate_scroll_amount,
    calibrate_tab_management,
    create_default_coordinates_config,
    get_coordinates_path,
    load_coordinates_config,
    open_calibration_article_tab,
    set_visible_articles,
)
from services.data_transfer import export_data_bundle, import_database_file
from storage.database import Database
from storage.file_store import FileStore
from gui.worker import (
    WorkerSignals, LinkCollectorWorker, ContentScraperWorker,
    RetryFailedWorker, GenerateIndexWorker, TestWorker
)
from gui.preview_dialog import ArticlePreviewDialog
from gui.styles import *


class WeChatScraperGUI:
    """Main GUI Application"""

    ARTICLE_LIST_BATCH_SIZE = 200

    def __init__(self):
        """Initialize the GUI application"""
        self.root = tk.Tk()
        self.root.title("微信公众号文章采集工具")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Database
        self.db = Database()
        self.file_store = FileStore()

        # Current worker
        self.current_worker = None
        self.worker_timer = None
        self.is_stopping = False  # Track if we're in the middle of stopping

        # Calibration UI state
        self.calibration_item_widgets = {}
        self.calibration_active_item = None
        self.calibration_action_after_id = None
        self.calibration_cancel_requested = False
        self.checked_article_ids = set()
        self.article_check_anchor_id = None
        self.article_list_refresh_token = 0
        self.article_search_after_id = None
        self.article_resize_after_id = None
        self.article_current_page = 1
        self.article_page_size = 20
        self.article_total_count = 0
        self.article_sort_column = None
        self.article_sort_descending = False
        self.article_checked_image = None
        self.article_unchecked_image = None

        self._setup_ui()
        self.root.bind_all("<Escape>", self._handle_escape_stop)
        self._update_statistics()

    def _call_on_ui_thread(self, func):
        """Run a callback on the Tk main loop and wait for its result."""
        result = {}
        completed = threading.Event()

        def runner():
            try:
                result["value"] = func()
            except Exception as exc:
                result["error"] = exc
            finally:
                completed.set()

        self.root.after(0, runner)
        completed.wait()

        if "error" in result:
            raise result["error"]

        return result.get("value")

    def _setup_ui(self):
        """Setup the main UI"""
        self._setup_tree_styles()
        self._setup_checkbox_images()

        # Create menu bar
        self._create_menu()

        # Create main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Create tabs
        self.dashboard_tab = self._create_dashboard_tab()
        self.calibration_tab = self._create_calibration_tab()
        self.collection_tab = self._create_collection_tab()
        self.scraping_tab = self._create_scraping_tab()
        self.articles_tab = self._create_articles_tab()

        # Status bar
        self._create_status_bar()
        self.root.bind("<Configure>", self._schedule_article_layout_refresh, add="+")
        self.root.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_global_mousewheel, add="+")
        self.root.bind_all("<Button-5>", self._on_global_mousewheel, add="+")

    def _create_scrollable_tab_container(self, tab_name):
        """Create a notebook tab with a vertically scrollable content area."""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=tab_name)
        tab_frame.columnconfigure(0, weight=1)
        tab_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(tab_frame, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        content_frame = ttk.Frame(canvas)
        content_frame._scroll_canvas = canvas
        canvas._scroll_canvas = canvas

        window_id = canvas.create_window((0, 0), window=content_frame, anchor="nw")

        content_frame.bind(
            "<Configure>",
            lambda _event, target_canvas=canvas: target_canvas.configure(scrollregion=target_canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event, target_canvas=canvas, target_window=window_id: target_canvas.itemconfigure(target_window, width=event.width),
        )

        return tab_frame, content_frame

    def _find_scroll_canvas(self, widget):
        """Find the nearest scrollable tab canvas for a widget."""
        current = widget
        while current is not None:
            canvas = getattr(current, "_scroll_canvas", None)
            if canvas is not None:
                return canvas
            current = getattr(current, "master", None)
        return None

    def _on_global_mousewheel(self, event):
        """Scroll the current tab page when the pointer is inside a scrollable tab."""
        widget = self.root.winfo_containing(event.x_root, event.y_root) or event.widget
        canvas = self._find_scroll_canvas(widget)
        if canvas is None:
            return

        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return
            direction = -1 if delta > 0 else 1

        canvas.yview_scroll(direction, "units")
        return "break"

    def _setup_tree_styles(self):
        """Configure treeview styles used by the GUI."""
        style = ttk.Style(self.root)
        style.configure("Articles.Treeview", rowheight=26, font=FONT_TABLE)
        style.layout(
            "Articles.Treeview.Heading",
            [
                (
                    "Treeheading.cell",
                    {
                        "sticky": "nswe",
                        "children": [
                            ("Treeheading.image", {"side": "right", "sticky": ""}),
                            ("Treeheading.text", {"sticky": "nswe"}),
                        ],
                    },
                )
            ],
        )
        style.configure(
            "Articles.Treeview.Heading",
            font=FONT_TABLE_HEADING,
            anchor=tk.CENTER,
            padding=(0, -3, 0, 0)
        )

    def _setup_checkbox_images(self):
        """Create checkbox images for the article list."""
        self.article_unchecked_image = self._create_checkbox_image(checked=False)
        self.article_checked_image = self._create_checkbox_image(checked=True)

    def _create_checkbox_image(self, checked, size=16):
        """Draw a checkbox image for use in the article list."""
        image = tk.PhotoImage(width=size, height=size)
        border = COLOR_PRIMARY if checked else "#7A7A7A"
        fill = "#E8F5E9" if checked else "#FFFFFF"

        image.put(fill, to=(1, 1, size - 1, size - 1))
        image.put(border, to=(0, 0, size, 1))
        image.put(border, to=(0, size - 1, size, size))
        image.put(border, to=(0, 0, 1, size))
        image.put(border, to=(size - 1, 0, size, size))

        if checked:
            check_color = COLOR_PRIMARY_DARK
            check_segments = [
                (3, 8, 5, 10),
                (5, 10, 7, 12),
                (7, 8, 9, 10),
                (9, 6, 11, 8),
                (11, 4, 13, 6),
            ]
            for x1, y1, x2, y2 in check_segments:
                image.put(check_color, to=(x1, y1, x2, y2))

        return image

    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入数据库", command=self._import_database)
        file_menu.add_command(label="导出数据包", command=self._export_data_bundle)
        file_menu.add_separator()
        file_menu.add_command(label="打开文章目录", command=self._open_articles_dir)
        file_menu.add_command(label="打开数据库位置", command=self._open_data_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="重新抓取失败文章", command=self._retry_failed)
        tools_menu.add_command(label="重新抓取无内容文章", command=self._retry_empty_articles)
        tools_menu.add_command(label="生成文章索引", command=self._generate_index)
        tools_menu.add_separator()
        tools_menu.add_command(label="刷新统计", command=self._update_statistics)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _create_dashboard_tab(self):
        """Create the dashboard tab"""
        tab_frame, frame = self._create_scrollable_tab_container(TAB_DASHBOARD)

        header = ttk.Frame(frame, padding=PAGE_PAD)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="微信公众号文章采集工具",
            font=("Helvetica", 20, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            header,
            text="三步采集公众号文章内容：坐标校准 → 链接采集 → 内容抓取",
            font=FONT_HELP,
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        stats_frame = ttk.Frame(frame, padding=(PAGE_PAD, 0, PAGE_PAD, 0))
        stats_frame.pack(fill=tk.X)

        self.stats_labels = {}

        stats_info = [
            ("total", "总文章数", COLOR_PRIMARY, "数据库中的文章记录"),
            ("pending", "待抓取", COLOR_WARNING, "等待进入内容抓取"),
            ("scraped", "已抓取", COLOR_SUCCESS, "已完成正文抓取"),
            ("failed", "抓取失败", COLOR_ERROR, "建议检查后重试"),
        ]

        for i, (key, label, color, hint) in enumerate(stats_info):
            card_frame = ttk.LabelFrame(stats_frame, text=label, padding=CONTROL_PAD)
            card_frame.grid(row=0, column=i, padx=(0 if i == 0 else SECTION_GAP, 0), pady=(0, SECTION_GAP), sticky="nsew")

            value_label = ttk.Label(
                card_frame,
                text="0",
                font=("Helvetica", 22, "bold"),
                foreground=color
            )
            value_label.pack()

            ttk.Label(
                card_frame,
                text=hint,
                font=FONT_HELP,
                foreground="gray"
            ).pack(pady=(4, 0))

            self.stats_labels[key] = value_label

        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)

        middle_frame = ttk.Frame(frame, padding=PAGE_PAD)
        middle_frame.pack(fill=tk.X)
        middle_frame.columnconfigure(0, weight=3)
        middle_frame.columnconfigure(1, weight=2)

        workflow_frame = ttk.LabelFrame(middle_frame, text="三步流程", padding=CONTROL_PAD)
        workflow_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SECTION_GAP))

        workflow_items = [
            ("坐标校准", "先完成微信窗口坐标校准，后续采集和抓取才能稳定运行。", self._go_to_calibration_tab),
            ("链接采集", "采集公众号文章链接，把文章基础记录写入本地数据库。", self._go_to_collection_tab),
            ("内容抓取", "抓取正文并生成 Markdown 备份，处理失败和无内容文章。", self._go_to_scraping_tab),
        ]

        for index, (title, description, command) in enumerate(workflow_items):
            row_frame = ttk.Frame(workflow_frame)
            row_frame.pack(fill=tk.X)
            row_frame.columnconfigure(0, weight=1)

            ttk.Label(row_frame, text=title, font=FONT_TITLE).grid(row=0, column=0, sticky="w")
            ttk.Label(
                row_frame,
                text=description,
                font=FONT_HELP,
                foreground="gray",
                wraplength=420,
                justify=tk.LEFT
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))
            ttk.Button(row_frame, text=f"前往{title}", command=command).grid(row=0, column=1, rowspan=2, padx=(SECTION_GAP, 0))

            if index < len(workflow_items) - 1:
                ttk.Separator(workflow_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=SECTION_GAP)

        todo_frame = ttk.LabelFrame(middle_frame, text="当前待办", padding=CONTROL_PAD)
        todo_frame.grid(row=0, column=1, sticky="nsew")

        self.dashboard_todo_summary_label = ttk.Label(
            todo_frame,
            text="正在检查当前状态...",
            font=FONT_LABEL
        )
        self.dashboard_todo_summary_label.pack(anchor=tk.W)

        self.dashboard_todo_container = ttk.Frame(todo_frame)
        self.dashboard_todo_container.pack(fill=tk.X, pady=(SECTION_GAP_SMALL, 0))

        bottom_frame = ttk.Frame(frame, padding=(PAGE_PAD, 0, PAGE_PAD, PAGE_PAD_SMALL))
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        recent_frame = ttk.LabelFrame(bottom_frame, text="最近文章", padding=CONTROL_PAD)
        recent_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            recent_frame,
            text="按发布时间显示最近 5 篇文章",
            font=FONT_HELP,
            foreground="gray"
        ).pack(anchor=tk.W)

        self.dashboard_recent_container = ttk.Frame(recent_frame)
        self.dashboard_recent_container.pack(fill=tk.BOTH, expand=True, pady=(SECTION_GAP_SMALL, 0))

        self.last_update_label = ttk.Label(
            frame,
            text="",
            font=("Helvetica", 8),
            foreground="gray"
        )
        self.last_update_label.pack(anchor=tk.W, padx=PAGE_PAD, pady=(0, SECTION_GAP_SMALL))

        return tab_frame

    def _create_collection_tab(self):
        """Create the link collection tab"""
        tab_frame, frame = self._create_scrollable_tab_container(TAB_COLLECTION)

        # Control frame
        control_frame = ttk.Frame(frame, padding=PAGE_PAD)
        control_frame.pack(fill=tk.X)

        # Calibration status
        self.calibration_status_label = ttk.Label(
            control_frame,
            text="校准状态: 未校准",
            font=("Helvetica", 10, "bold"),
            foreground=COLOR_WARNING
        )
        self.calibration_status_label.pack(anchor=tk.W)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(SECTION_GAP, SECTION_GAP))

        # Start/Stop button
        self.collect_button = ttk.Button(
            control_frame,
            text="开始采集",
            command=self._start_collection
        )
        self.collect_button.pack(side=tk.LEFT, padx=(0, 10))

        self.collect_stop_button = ttk.Button(
            control_frame,
            text="停止",
            command=self._stop_worker,
            state=tk.DISABLED
        )
        self.collect_stop_button.pack(side=tk.LEFT, padx=(0, 10))

        # Preparation checklist
        checklist_frame = ttk.LabelFrame(frame, text="准备工作检查", padding=CONTROL_PAD)
        checklist_frame.pack(fill=tk.X, padx=PAGE_PAD, pady=(0, SECTION_GAP))

        checklist_items = [
            "窗口1：已打开公众号页面，并点击【文章分组】，滚动到页面最顶部",
            "窗口2：已打开微信内置浏览器",
            "两个窗口不重叠且都可见",
            "已完成坐标校准"
        ]

        for item in checklist_items:
            ttk.Label(checklist_frame, text=f"  {item}", font=FONT_HELP_LARGE).pack(anchor=tk.W)

        # Progress frame
        progress_frame = ttk.Frame(frame, padding=(PAGE_PAD, 0, PAGE_PAD, 0))
        progress_frame.pack(fill=tk.X)

        ttk.Label(progress_frame, text="采集进度:").pack(anchor=tk.W)

        self.collect_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100
        )
        self.collect_progress.pack(fill=tk.X, pady=5)

        self.collect_status_label = ttk.Label(progress_frame, text="")
        self.collect_status_label.pack(anchor=tk.W)

        # Log frame
        log_frame = ttk.LabelFrame(frame, text="采集日志", padding=PAGE_PAD_SMALL)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=PAGE_PAD, pady=(SECTION_GAP, PAGE_PAD_SMALL))

        self.collect_log = scrolledtext.ScrolledText(
            log_frame,
            height=LOG_HEIGHT,
            font=FONT_LOG,
            wrap=tk.WORD
        )
        self.collect_log.pack(fill=tk.BOTH, expand=True)

        return tab_frame

    def _create_scraping_tab(self):
        """Create the content scraping tab"""
        tab_frame, frame = self._create_scrollable_tab_container(TAB_SCRAPING)

        # Control frame
        control_frame = ttk.Frame(frame, padding=PAGE_PAD)
        control_frame.pack(fill=tk.X)

        # Pending count
        self.scrape_pending_label = ttk.Label(
            control_frame,
            text="待抓取文章: 0 篇",
            font=("Helvetica", 10, "bold")
        )
        self.scrape_pending_label.pack(anchor=tk.W)

        self.scrape_empty_label = ttk.Label(
            control_frame,
            text="无内容文章: 0 篇",
            font=("Helvetica", 10),
            foreground=COLOR_WARNING
        )
        self.scrape_empty_label.pack(anchor=tk.W, pady=(4, 0))

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=SECTION_GAP)

        # Start/Stop button
        self.scrape_button = ttk.Button(
            control_frame,
            text="开始抓取",
            command=self._start_scraping
        )
        self.scrape_button.pack(side=tk.LEFT, padx=(0, 10))

        self.scrape_stop_button = ttk.Button(
            control_frame,
            text="停止",
            command=self._stop_worker,
            state=tk.DISABLED
        )
        self.scrape_stop_button.pack(side=tk.LEFT)

        ttk.Button(
            control_frame,
            text="重抓无内容文章",
            command=self._retry_empty_articles
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Counters
        counters_frame = ttk.Frame(control_frame)
        counters_frame.pack(side=tk.RIGHT)

        self.scrape_success_label = ttk.Label(counters_frame, text="成功: 0", foreground=COLOR_SUCCESS)
        self.scrape_success_label.pack(side=tk.LEFT, padx=SECTION_GAP)

        self.scrape_failed_label = ttk.Label(counters_frame, text="失败: 0", foreground=COLOR_ERROR)
        self.scrape_failed_label.pack(side=tk.LEFT, padx=SECTION_GAP)

        # Progress frame
        progress_frame = ttk.Frame(frame, padding=(PAGE_PAD, 0, PAGE_PAD, 0))
        progress_frame.pack(fill=tk.X)

        ttk.Label(progress_frame, text="抓取进度:").pack(anchor=tk.W)

        self.scrape_progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            maximum=100
        )
        self.scrape_progress.pack(fill=tk.X, pady=5)

        self.scrape_status_label = ttk.Label(progress_frame, text="")
        self.scrape_status_label.pack(anchor=tk.W)

        # Log frame
        log_frame = ttk.LabelFrame(frame, text="抓取日志", padding=PAGE_PAD_SMALL)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=PAGE_PAD, pady=(SECTION_GAP, PAGE_PAD_SMALL))

        self.scrape_log = scrolledtext.ScrolledText(
            log_frame,
            height=LOG_HEIGHT,
            font=FONT_LOG,
            wrap=tk.WORD
        )
        self.scrape_log.pack(fill=tk.BOTH, expand=True)

        return tab_frame

    def _create_articles_tab(self):
        """Create the articles management tab"""
        tab_frame, frame = self._create_scrollable_tab_container(TAB_ARTICLES)

        # Control frame
        control_frame = ttk.Frame(frame, padding=PAGE_PAD)
        control_frame.pack(fill=tk.X)

        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill=tk.X)

        # Filter
        ttk.Label(filter_frame, text="状态筛选:").pack(side=tk.LEFT)

        self.article_filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.article_filter_var,
            values=["all", "pending", "scraped", "failed", "empty"],
            state="readonly",
            width=10
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self._reset_article_list_page)

        # Search
        ttk.Label(filter_frame, text="搜索:").pack(side=tk.LEFT, padx=(20, 5))

        self.article_search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.article_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        search_entry.bind("<KeyRelease>", self._schedule_article_search_refresh)

        ttk.Button(
            filter_frame,
            text="刷新列表",
            command=self._refresh_article_list
        ).pack(side=tk.RIGHT, padx=(10, 0))

        selection_frame = ttk.Frame(control_frame, padding=(0, SECTION_GAP, 0, 0))
        selection_frame.pack(fill=tk.X)

        self.article_selection_label = ttk.Label(
            selection_frame,
            text="已勾选 0 篇",
            foreground="gray"
        )
        self.article_selection_label.pack(side=tk.LEFT)

        ttk.Button(
            selection_frame,
            text="全选当前列表",
            command=self._check_all_visible_articles
        ).pack(side=tk.RIGHT, padx=(8, 0))

        ttk.Button(
            selection_frame,
            text="清空选择",
            command=self._clear_checked_articles
        ).pack(side=tk.RIGHT)

        action_frame = ttk.Frame(control_frame, padding=(0, SECTION_GAP, 0, 0))
        action_frame.pack(fill=tk.X)

        primary_actions_row = ttk.Frame(action_frame)
        primary_actions_row.pack(fill=tk.X)

        secondary_actions_row = ttk.Frame(action_frame)
        secondary_actions_row.pack(fill=tk.X, pady=(SECTION_GAP_SMALL, 0))

        self.retry_selected_button = ttk.Button(
            primary_actions_row,
            text="重新抓取选中",
            command=self._retry_selected_articles
        )
        self.retry_selected_button.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            primary_actions_row,
            text="重新抓取失败文章",
            command=self._retry_failed
        ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            primary_actions_row,
            text="重新抓取无内容文章",
            command=self._retry_empty_articles
        ).pack(side=tk.LEFT, padx=8)

        self.export_selected_button = ttk.Button(
            secondary_actions_row,
            text="导出选中",
            command=self._export_selected_article
        )
        self.export_selected_button.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(
            secondary_actions_row,
            text="批量导出",
            command=self._export_articles_batch
        ).pack(side=tk.LEFT, padx=8)

        self.delete_selected_button = ttk.Button(
            secondary_actions_row,
            text="删除选中",
            command=self._delete_selected_articles,
        )
        self.delete_selected_button.pack(side=tk.LEFT, padx=8)

        ttk.Label(
            secondary_actions_row,
            text="批量导出默认使用当前选中；删除会同时移除数据库记录和本地备份文件。",
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(12, 0))

        pagination_frame = ttk.Frame(control_frame, padding=(0, SECTION_GAP, 0, 0))
        pagination_frame.pack(fill=tk.X)

        self.article_page_info_label = ttk.Label(
            pagination_frame,
            text="第 1 / 1 页，共 0 篇",
            foreground="gray"
        )
        self.article_page_info_label.pack(side=tk.LEFT)

        self.article_prev_page_button = ttk.Button(
            pagination_frame,
            text="上一页",
            command=lambda: self._change_article_page(-1)
        )
        self.article_prev_page_button.pack(side=tk.RIGHT)

        self.article_next_page_button = ttk.Button(
            pagination_frame,
            text="下一页",
            command=lambda: self._change_article_page(1)
        )
        self.article_next_page_button.pack(side=tk.RIGHT, padx=(8, 0))

        ttk.Label(pagination_frame, text="每页:").pack(side=tk.RIGHT, padx=(12, 4))

        self.article_page_size_var = tk.StringVar(value=str(self.article_page_size))
        page_size_combo = ttk.Combobox(
            pagination_frame,
            textvariable=self.article_page_size_var,
            values=["10", "20", "50"],
            state="normal",
            width=6
        )
        page_size_combo.pack(side=tk.RIGHT)
        page_size_combo.bind("<<ComboboxSelected>>", self._on_article_page_size_change)
        page_size_combo.bind("<Return>", self._on_article_page_size_change)
        page_size_combo.bind("<FocusOut>", self._on_article_page_size_change)

        # Treeview for articles
        tree_frame = ttk.Frame(frame, padding=PAGE_PAD_SMALL)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=PAGE_PAD, pady=(2, PAGE_PAD_SMALL))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.articles_tree = ttk.Treeview(
            tree_frame,
            columns=("title", "url", "publish_time", "status"),
            show="tree headings",
            selectmode="browse",
            style="Articles.Treeview"
        )

        self.articles_tree.heading("#0", text="选择")
        self.articles_tree.heading("title", text="标题", command=lambda: self._toggle_article_sort("title"))
        self.articles_tree.heading("url", text="链接")
        self.articles_tree.heading(
            "publish_time",
            text="发布时间",
            command=lambda: self._toggle_article_sort("publish_time")
        )
        self.articles_tree.heading("status", text="状态")
        self.articles_tree.heading("#0", anchor=tk.CENTER)
        self.articles_tree.heading("title", anchor=tk.CENTER)
        self.articles_tree.heading("url", anchor=tk.CENTER)
        self.articles_tree.heading("publish_time", anchor=tk.CENTER)
        self.articles_tree.heading("status", anchor=tk.CENTER)

        self.articles_tree.column("#0", anchor=tk.CENTER, minwidth=60, width=64, stretch=False)
        self.articles_tree.column("title", anchor=tk.W, minwidth=180, stretch=True)
        self.articles_tree.column("url", anchor=tk.W, minwidth=220, stretch=True)
        self.articles_tree.column("publish_time", anchor=tk.CENTER, minwidth=130, stretch=False)
        self.articles_tree.column("status", anchor=tk.CENTER, minwidth=80, stretch=False)
        self.articles_tree.tag_configure("empty_content", foreground=COLOR_WARNING)

        self.articles_tree.bind("<Button-1>", self._on_articles_tree_click)
        self.articles_tree.bind("<Double-1>", self._on_article_double_click)
        self.articles_tree.bind("<Control-a>", self._check_all_visible_articles)
        self.articles_tree.bind("<Command-a>", self._check_all_visible_articles)
        self.articles_tree.bind("<Configure>", self._resize_articles_columns)

        self.articles_tree.grid(row=0, column=0, sticky="nsew")

        self.root.after(0, self._resize_articles_columns)
        self.root.after(0, self._update_article_sort_headings)
        self.root.after(0, self._update_article_selection_actions)

        return tab_frame

    def _create_calibration_tab(self):
        """Create the page-based calibration tab."""
        tab_frame, frame = self._create_scrollable_tab_container(TAB_CALIBRATION)

        header = ttk.Frame(frame, padding=PAGE_PAD)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="坐标校准",
            font=("Helvetica", 16, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            header,
            text="按需逐项校准关键坐标，不需要再从头跑完整段向导。",
            font=FONT_HELP,
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        ttk.Separator(header, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=PAGE_PAD_SMALL)

        action_frame = ttk.Frame(header)
        action_frame.pack(anchor=tk.W)

        self.test_button = ttk.Button(
            action_frame,
            text="测试坐标",
            command=self._start_test
        )
        self.test_button.pack(side=tk.LEFT)

        ttk.Button(
            action_frame,
            text="刷新状态",
            command=self._refresh_calibration_items
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.calibration_page_status_label = ttk.Label(
            header,
            text="正在读取校准状态...",
            font=FONT_HELP_LARGE,
            foreground=COLOR_PRIMARY_DARK,
        )
        self.calibration_page_status_label.pack(anchor=tk.W, pady=(SECTION_GAP, 0))

        operation_frame = ttk.LabelFrame(frame, text="当前操作", padding=CONTROL_PAD)
        operation_frame.pack(fill=tk.X, padx=PAGE_PAD, pady=(0, SECTION_GAP))

        self.calibration_action_label = ttk.Label(
            operation_frame,
            text="当前没有进行中的校准项。",
            font=FONT_HELP,
            foreground="gray",
            justify=tk.LEFT,
        )
        self.calibration_action_label.pack(anchor=tk.W)

        self.calibration_cancel_button = ttk.Button(
            operation_frame,
            text="取消当前校准",
            command=self._cancel_active_calibration_action,
            state=tk.DISABLED,
        )
        self.calibration_cancel_button.pack(anchor=tk.W, pady=(SECTION_GAP_SMALL, 0))

        items_frame = ttk.Frame(frame, padding=(PAGE_PAD, 0, PAGE_PAD, 0))
        items_frame.pack(fill=tk.BOTH, expand=True)
        items_frame.columnconfigure(0, weight=1)

        article_group = ttk.LabelFrame(items_frame, text="文章列表", padding=CONTROL_PAD)
        article_group.pack(fill=tk.X, pady=(0, SECTION_GAP))
        self._create_calibration_item_row(
            article_group,
            item_id="article_click_area",
            title="文章点击位置",
            description="通过两次文章顶部和一次文章底部位置，自动计算点击点和行高。",
            command=self._start_article_click_area_calibration,
        )
        self._create_calibration_item_row(
            article_group,
            item_id="scroll_amount",
            title="滚动单位",
            description="记录滚动前后同一参考点，自动计算每次滚动的单位值。",
            command=self._start_scroll_amount_calibration,
        )
        self._create_calibration_item_row(
            article_group,
            item_id="visible_articles",
            title="可见文章数",
            description="设置当前窗口中同时能看到的文章数量，用于处理最后一屏。",
            command=self._start_visible_articles_calibration,
            action_text="设置",
        )

        browser_group = ttk.LabelFrame(items_frame, text="浏览器菜单", padding=CONTROL_PAD)
        browser_group.pack(fill=tk.X, pady=(0, SECTION_GAP))
        self._create_calibration_item_row(
            browser_group,
            item_id="more_button",
            title="更多按钮",
            description="记录微信内置浏览器右上角“更多”按钮的位置。",
            command=self._start_more_button_calibration,
        )
        self._create_calibration_item_row(
            browser_group,
            item_id="copy_link_menu",
            title="复制链接菜单",
            description="启动倒计时后，在微信里打开“更多”菜单并把鼠标停在“复制链接”上。",
            command=self._start_copy_link_menu_calibration,
        )

        tabs_group = ttk.LabelFrame(items_frame, text="标签管理", padding=CONTROL_PAD)
        tabs_group.pack(fill=tk.X)
        self._create_calibration_item_row(
            tabs_group,
            item_id="tab_management",
            title="标签管理",
            description="自动打开 20 个标签后，依次记录第一个标签和关闭按钮位置。",
            command=self._start_tab_management_calibration,
        )

        info_frame = ttk.LabelFrame(frame, text="校准说明", padding=CONTROL_PAD)
        info_frame.pack(fill=tk.X, padx=PAGE_PAD, pady=(SECTION_GAP, PAGE_PAD_SMALL))

        info_text = """
请根据需要点击某一项开始校准，不需要再一次性完成全部步骤。

操作说明：
- 每个项目只会弹出当前这一步需要的小提示框
- 建议把鼠标移动到目标位置后，用键盘 Enter 确认弹窗
- 需要自动动作的项目（复制链接菜单、标签管理）会在页面里显示当前进度

注意事项：
- 校准后请勿移动微信窗口的位置和大小
- 如窗口位置改变，需要重新校准相关项目
- 建议保持公众号窗口和微信内置浏览器窗口都可见
"""
        ttk.Label(info_frame, text=info_text, font=FONT_HELP_LARGE, justify=tk.LEFT).pack(anchor=tk.W)

        self.root.after(0, self._refresh_calibration_items)

        return tab_frame

    def _create_status_bar(self):
        """Create the status bar"""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(STATUS_PAD_X, STATUS_PAD_Y))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)

        self.status_label = ttk.Label(status_frame, text=STATUS_IDLE)
        self.status_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=STATUS_PAD_X)

        self.worker_status_label = ttk.Label(status_frame, text="")
        self.worker_status_label.pack(side=tk.LEFT)

    def _go_to_calibration_tab(self):
        """Open the calibration tab from the dashboard."""
        self.notebook.select(self.calibration_tab)
        self._refresh_calibration_items()

    def _go_to_collection_tab(self):
        """Open the collection tab from the dashboard."""
        self.notebook.select(self.collection_tab)

    def _go_to_scraping_tab(self):
        """Open the scraping tab from the dashboard."""
        self.notebook.select(self.scraping_tab)

    def _create_calibration_item_row(self, parent, *, item_id, title, description, command, action_text="校准"):
        """Create one row in the page-based calibration list."""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=(0, SECTION_GAP))

        content = ttk.Frame(row)
        content.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(content, text=title, font=FONT_TITLE).pack(anchor=tk.W)
        ttk.Label(
            content,
            text=description,
            font=FONT_HELP,
            foreground="gray",
            justify=tk.LEFT,
            wraplength=620,
        ).pack(anchor=tk.W, pady=(SECTION_GAP_SMALL, 0))

        meta = ttk.Frame(content)
        meta.pack(fill=tk.X, pady=(SECTION_GAP_SMALL, 0))

        status_label = ttk.Label(meta, text="未校准", font=FONT_HELP, foreground=COLOR_WARNING)
        status_label.pack(side=tk.LEFT)

        value_label = ttk.Label(meta, text="", font=FONT_HELP, foreground="gray")
        value_label.pack(side=tk.LEFT, padx=(SECTION_GAP, 0))

        action_button = ttk.Button(row, text=action_text, command=command)
        action_button.pack(side=tk.RIGHT)

        self.calibration_item_widgets[item_id] = {
            "status_label": status_label,
            "value_label": value_label,
            "action_button": action_button,
            "default_action_text": action_text,
        }

    def _is_calibration_point_configured(self, point):
        """Return whether a stored point looks calibrated instead of defaulted."""
        if not isinstance(point, dict):
            return False
        return bool(point.get("x") or point.get("y"))

    def _format_calibration_point(self, point):
        """Render a stored point for the calibration page."""
        if not self._is_calibration_point_configured(point):
            return "未记录"
        return f"({point.get('x')}, {point.get('y')})"

    def _set_calibration_action_text(self, text, color="gray"):
        """Update the on-page calibration action message."""
        if hasattr(self, "calibration_action_label"):
            self.calibration_action_label.config(text=text, foreground=color)
        self.worker_status_label.config(text=text)

    def _clear_calibration_after(self):
        """Cancel any scheduled page-calibration callback."""
        if self.calibration_action_after_id is not None:
            try:
                self.root.after_cancel(self.calibration_action_after_id)
            except Exception:
                pass
            self.calibration_action_after_id = None

    def _schedule_calibration_after(self, delay_ms, callback):
        """Schedule the next asynchronous calibration step."""
        self._clear_calibration_after()
        self.calibration_action_after_id = self.root.after(delay_ms, callback)

    def _set_calibration_buttons_state(self, disabled):
        """Enable or disable page calibration actions."""
        worker_busy = bool(self.current_worker and self.current_worker.is_alive())
        state = tk.DISABLED if disabled or worker_busy else tk.NORMAL
        for widgets in self.calibration_item_widgets.values():
            widgets["action_button"].config(state=state)
        if hasattr(self, "test_button"):
            self.test_button.config(state=tk.DISABLED if disabled or worker_busy else tk.NORMAL)
        if hasattr(self, "calibration_cancel_button"):
            self.calibration_cancel_button.config(state=tk.NORMAL if disabled else tk.DISABLED)

    def _refresh_calibration_items(self):
        """Refresh calibration item values and statuses from config."""
        config_exists = get_coordinates_path().exists()
        config = load_coordinates_config(create_if_missing=False)
        defaults = create_default_coordinates_config()

        article_list = config["windows"]["article_list"]
        browser = config["windows"]["browser"]
        default_article = defaults["windows"]["article_list"]

        article_click = article_list.get("article_click_area", {})
        row_height = int(article_list.get("row_height") or 0)
        scroll_amount = int(article_list.get("scroll_amount") or default_article["scroll_amount"])
        visible_articles = int(article_list.get("visible_articles") or default_article["visible_articles"])
        more_button = browser.get("more_button", {})
        copy_link = browser.get("copy_link_menu", {})
        first_tab = browser.get("first_tab", {})
        close_button = browser.get("close_tab_button", {})

        article_ready = config_exists and self._is_calibration_point_configured(article_click) and row_height > 0
        scroll_ready = article_ready and scroll_amount > 0 and scroll_amount != default_article["scroll_amount"]
        scroll_default = article_ready and scroll_amount == default_article["scroll_amount"]
        visible_default = visible_articles == default_article["visible_articles"]
        more_ready = config_exists and self._is_calibration_point_configured(more_button)
        copy_ready = config_exists and self._is_calibration_point_configured(copy_link)
        tab_ready = config_exists and self._is_calibration_point_configured(first_tab) and self._is_calibration_point_configured(close_button)

        self._update_calibration_row(
            "article_click_area",
            status_text="已校准" if article_ready else "未校准",
            status_color=COLOR_SUCCESS if article_ready else COLOR_WARNING,
            value_text=f"点击点: {self._format_calibration_point(article_click)}  |  行高: {row_height if row_height > 0 else '未记录'}",
            recalibrate=article_ready,
        )
        if scroll_ready:
            scroll_status_text = "已校准"
            scroll_status_color = COLOR_SUCCESS
        elif scroll_default:
            scroll_status_text = "默认值"
            scroll_status_color = COLOR_INFO
        else:
            scroll_status_text = "未校准"
            scroll_status_color = COLOR_WARNING
        self._update_calibration_row(
            "scroll_amount",
            status_text=scroll_status_text,
            status_color=scroll_status_color,
            value_text=f"当前值: {scroll_amount}",
            recalibrate=article_ready,
        )
        self._update_calibration_row(
            "visible_articles",
            status_text="默认值" if visible_default else "已设置",
            status_color=COLOR_INFO if visible_default else COLOR_SUCCESS,
            value_text=f"当前值: {visible_articles}",
            recalibrate=not visible_default,
        )
        self._update_calibration_row(
            "more_button",
            status_text="已校准" if more_ready else "未校准",
            status_color=COLOR_SUCCESS if more_ready else COLOR_WARNING,
            value_text=f"当前位置: {self._format_calibration_point(more_button)}",
            recalibrate=more_ready,
        )
        self._update_calibration_row(
            "copy_link_menu",
            status_text="已校准" if copy_ready else "未校准",
            status_color=COLOR_SUCCESS if copy_ready else COLOR_WARNING,
            value_text=f"当前位置: {self._format_calibration_point(copy_link)}",
            recalibrate=copy_ready,
        )
        self._update_calibration_row(
            "tab_management",
            status_text="已校准" if tab_ready else "未校准",
            status_color=COLOR_SUCCESS if tab_ready else COLOR_WARNING,
            value_text=(
                f"第一个标签: {self._format_calibration_point(first_tab)}  |  "
                f"关闭按钮: {self._format_calibration_point(close_button)}"
            ),
            recalibrate=tab_ready,
        )

        visible_ready = config_exists or not visible_default
        ready_count = sum([article_ready, scroll_ready or scroll_default, visible_ready, more_ready, copy_ready, tab_ready])
        if hasattr(self, "calibration_page_status_label"):
            self.calibration_page_status_label.config(
                text=f"当前共有 6 项可维护，已就绪 {ready_count} 项，可按需重校准任一项目。",
                foreground=COLOR_PRIMARY_DARK,
            )

        self._set_calibration_buttons_state(bool(self.calibration_active_item))

    def _update_calibration_row(self, item_id, *, status_text, status_color, value_text, recalibrate):
        """Update one calibration row's visible state."""
        widgets = self.calibration_item_widgets.get(item_id)
        if not widgets:
            return
        widgets["status_label"].config(text=status_text, foreground=status_color)
        widgets["value_label"].config(text=value_text)
        default_text = widgets["default_action_text"]
        if default_text == "设置":
            action_text = "重新设置" if recalibrate else "设置"
        else:
            action_text = "重校准" if recalibrate else "校准"
        widgets["action_button"].config(text=action_text)

    def _begin_calibration_action(self, item_id, title):
        """Start one page-level calibration action."""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行，请先等待当前任务完成")
            return False
        if self.calibration_active_item:
            messagebox.showinfo("提示", "已有进行中的校准项，请先完成或取消当前校准")
            return False

        self.calibration_active_item = item_id
        self.calibration_cancel_requested = False
        self._set_calibration_buttons_state(True)
        self._set_calibration_action_text(f"当前项目：{title}", COLOR_PRIMARY_DARK)
        return True

    def _finish_calibration_action(self, *, success_message=None, cancelled=False, error_message=None):
        """Finish the current page-level calibration action."""
        self._clear_calibration_after()
        self.calibration_active_item = None
        self.calibration_cancel_requested = False

        if error_message:
            self._set_calibration_action_text(f"校准失败：{error_message}", COLOR_ERROR)
            messagebox.showerror("校准失败", error_message, parent=self.root)
        elif cancelled:
            self._set_calibration_action_text("当前校准已取消。", COLOR_WARNING)
        elif success_message:
            self._set_calibration_action_text(success_message, COLOR_SUCCESS)
        else:
            self._set_calibration_action_text("当前没有进行中的校准项。", "gray")

        self._refresh_calibration_items()
        self._update_statistics()

    def _cancel_active_calibration_action(self):
        """Cancel the active page-based calibration flow."""
        if not self.calibration_active_item:
            return
        self.calibration_cancel_requested = True
        self._finish_calibration_action(cancelled=True)

    def _prompt_calibration_position(self, title, prompt):
        """Ask the user to confirm and then capture the current mouse position."""
        import pyautogui

        confirmed = messagebox.askokcancel(
            title,
            f"{prompt}\n\n确认后将记录当前鼠标位置（建议按 Enter 确认）",
            parent=self.root,
        )
        if not confirmed or self.calibration_cancel_requested:
            return None
        return pyautogui.position()

    def _start_article_click_area_calibration(self):
        """Calibrate article click area and row height."""
        if not self._begin_calibration_action("article_click_area", "文章点击位置"):
            return

        try:
            first_top = self._prompt_calibration_position(
                "文章点击位置",
                "步骤 1/3：请将鼠标移动到【任意一篇文章的顶部】。",
            )
            if first_top is None:
                self._finish_calibration_action(cancelled=True)
                return

            second_top = self._prompt_calibration_position(
                "文章点击位置",
                "步骤 2/3：请将鼠标移动到【下一篇文章的顶部】。",
            )
            if second_top is None:
                self._finish_calibration_action(cancelled=True)
                return

            first_bottom = self._prompt_calibration_position(
                "文章点击位置",
                "步骤 3/3：请将鼠标移动到【第一篇文章的底部】。",
            )
            if first_bottom is None:
                self._finish_calibration_action(cancelled=True)
                return

            result = calibrate_article_click_area(
                first_top=first_top,
                second_top=second_top,
                first_bottom=first_bottom,
            )
            click_area = result["click_area"]
            self._finish_calibration_action(
                success_message=f"文章点击位置已保存：({click_area['x']}, {click_area['y']}), 行高 {result['row_height']} 像素。",
            )
        except Exception as exc:
            self._finish_calibration_action(error_message=str(exc))

    def _start_scroll_amount_calibration(self):
        """Calibrate scroll amount from two reference points."""
        if not self._begin_calibration_action("scroll_amount", "滚动单位"):
            return

        try:
            config = load_coordinates_config(create_if_missing=False)
            row_height = int(config["windows"]["article_list"].get("row_height") or 0)
            if row_height <= 0:
                raise ValueError("请先完成“文章点击位置”校准，再计算滚动单位。")

            before_scroll = self._prompt_calibration_position(
                "滚动单位",
                "步骤 1/2：请将鼠标移动到文章列表中的某个参考点，确认后系统会自动滚动 1 单位。",
            )
            if before_scroll is None:
                self._finish_calibration_action(cancelled=True)
                return

            import pyautogui

            click_area = config["windows"]["article_list"]["article_click_area"]
            pyautogui.moveTo(click_area["x"], click_area["y"], 0.2)
            pyautogui.scroll(-1)
            self._set_calibration_action_text("滚动单位：已自动滚动 1 单位，请准备记录滚动后的同一参考点。", COLOR_PRIMARY_DARK)

            def capture_after_scroll():
                if self.calibration_cancel_requested:
                    self._finish_calibration_action(cancelled=True)
                    return

                try:
                    after_scroll = self._prompt_calibration_position(
                        "滚动单位",
                        "步骤 2/2：请将鼠标移动到【滚动后的同一参考点】。",
                    )
                    if after_scroll is None:
                        self._finish_calibration_action(cancelled=True)
                        return

                    result = calibrate_scroll_amount(
                        before_scroll=before_scroll,
                        after_scroll=after_scroll,
                    )
                    self._finish_calibration_action(
                        success_message=f"滚动单位已保存：{result['scroll_amount']}（参考像素差 {result['pixels_per_unit']}）。",
                    )
                except Exception as exc:
                    self._finish_calibration_action(error_message=str(exc))

            self._schedule_calibration_after(1000, capture_after_scroll)
        except Exception as exc:
            self._finish_calibration_action(error_message=str(exc))

    def _start_visible_articles_calibration(self):
        """Set the visible article count."""
        if not self._begin_calibration_action("visible_articles", "可见文章数"):
            return

        try:
            config = load_coordinates_config(create_if_missing=False)
            default_value = int(config["windows"]["article_list"].get("visible_articles") or 5)
            visible_count = simpledialog.askinteger(
                "可见文章数",
                "请输入当前窗口中同时可见的文章数量：",
                initialvalue=default_value,
                minvalue=1,
                parent=self.root,
            )
            if visible_count is None:
                self._finish_calibration_action(cancelled=True)
                return

            result = set_visible_articles(visible_count=visible_count)
            self._finish_calibration_action(
                success_message=f"可见文章数已保存：{result['visible_count']}。",
            )
        except Exception as exc:
            self._finish_calibration_action(error_message=str(exc))

    def _start_more_button_calibration(self):
        """Capture the browser more-button position."""
        if not self._begin_calibration_action("more_button", "更多按钮"):
            return

        try:
            position = self._prompt_calibration_position(
                "更多按钮",
                "请将鼠标移动到微信内置浏览器右上角【更多】按钮。",
            )
            if position is None:
                self._finish_calibration_action(cancelled=True)
                return

            result = calibrate_more_button(position=position)
            saved = result["position"]
            self._finish_calibration_action(
                success_message=f"更多按钮已保存：({saved['x']}, {saved['y']})。",
            )
        except Exception as exc:
            self._finish_calibration_action(error_message=str(exc))

    def _start_copy_link_menu_calibration(self):
        """Run the countdown flow for the copy-link menu item."""
        if not self._begin_calibration_action("copy_link_menu", "复制链接菜单"):
            return

        confirmed = messagebox.askokcancel(
            "复制链接菜单",
            "确认后将开始倒计时。\n\n请在倒计时内完成：\n"
            "1. 点击右上角【更多】按钮打开菜单\n"
            "2. 将鼠标移动到【复制链接】菜单项上并保持不动",
            parent=self.root,
        )
        if not confirmed:
            self._finish_calibration_action(cancelled=True)
            return

        def countdown(seconds_left):
            if self.calibration_cancel_requested:
                self._finish_calibration_action(cancelled=True)
                return

            if seconds_left > 0:
                self._set_calibration_action_text(
                    f"复制链接菜单：倒计时 {seconds_left} 秒，请在微信中打开菜单并将鼠标停在目标项上。",
                    COLOR_PRIMARY_DARK,
                )
                self._schedule_calibration_after(1000, lambda: countdown(seconds_left - 1))
                return

            try:
                import pyautogui

                result = calibrate_copy_link_menu(position=pyautogui.position())
                saved = result["position"]
                self._finish_calibration_action(
                    success_message=f"复制链接菜单已保存：({saved['x']}, {saved['y']})。",
                )
            except Exception as exc:
                self._finish_calibration_action(error_message=str(exc))

        countdown(COPY_LINK_COUNTDOWN_SECONDS)

    def _start_tab_management_calibration(self):
        """Auto-open tabs, then capture the tab-management coordinates."""
        if not self._begin_calibration_action("tab_management", "标签管理"):
            return

        config = load_coordinates_config(create_if_missing=False)
        click_area = config["windows"]["article_list"].get("article_click_area") or {}
        if not self._is_calibration_point_configured(click_area):
            self._finish_calibration_action(error_message="请先完成“文章点击位置”校准，再进行标签管理校准。")
            return

        confirmed = messagebox.askokcancel(
            "标签管理",
            "确认后，程序会自动点击文章 20 次以打开标签。\n\n"
            "请确保微信窗口已就绪，且不要移动鼠标或窗口。\n"
            "如需中止，可点击页面上的“取消当前校准”。",
            parent=self.root,
        )
        if not confirmed:
            self._finish_calibration_action(cancelled=True)
            return

        import pyautogui

        def open_next_tab(index):
            if self.calibration_cancel_requested:
                self._finish_calibration_action(cancelled=True)
                return

            if index >= OPEN_TABS_CLICKS:
                try:
                    first_tab = self._prompt_calibration_position(
                        "标签管理",
                        "步骤 1/2：请将鼠标移动到【第一个标签】上。",
                    )
                    if first_tab is None:
                        self._finish_calibration_action(cancelled=True)
                        return

                    close_button = self._prompt_calibration_position(
                        "标签管理",
                        "步骤 2/2：请将鼠标移动到【标签关闭按钮】上。",
                    )
                    if close_button is None:
                        self._finish_calibration_action(cancelled=True)
                        return

                    result = calibrate_tab_management(
                        first_tab=first_tab,
                        close_button=close_button,
                    )
                    saved_first = result["first_tab"]
                    saved_close = result["close_button"]
                    self._finish_calibration_action(
                        success_message=(
                            "标签管理已保存："
                            f"第一个标签 ({saved_first['x']}, {saved_first['y']}), "
                            f"关闭按钮 ({saved_close['x']}, {saved_close['y']})。"
                        ),
                    )
                except Exception as exc:
                    self._finish_calibration_action(error_message=str(exc))
                return

            try:
                self._set_calibration_action_text(
                    f"标签管理：正在自动打开标签 {index + 1}/{OPEN_TABS_CLICKS}...",
                    COLOR_PRIMARY_DARK,
                )
                open_calibration_article_tab(click=pyautogui.click)
                self._schedule_calibration_after(2000, lambda: open_next_tab(index + 1))
            except Exception as exc:
                self._finish_calibration_action(error_message=str(exc))

        open_next_tab(0)

    def _get_calibration_overall_state(self):
        """Return overall calibration readiness for dashboard/status display."""
        if not get_coordinates_path().exists():
            return "none"

        config = load_coordinates_config(create_if_missing=False)
        defaults = create_default_coordinates_config()
        article_list = config["windows"]["article_list"]
        browser = config["windows"]["browser"]

        article_ready = self._is_calibration_point_configured(article_list.get("article_click_area")) and int(article_list.get("row_height") or 0) > 0
        scroll_amount = int(article_list.get("scroll_amount") or 0)
        scroll_ready = article_ready and scroll_amount > 0
        visible_ready = int(article_list.get("visible_articles") or 0) > 0
        more_ready = self._is_calibration_point_configured(browser.get("more_button"))
        copy_ready = self._is_calibration_point_configured(browser.get("copy_link_menu"))
        tab_ready = self._is_calibration_point_configured(browser.get("first_tab")) and self._is_calibration_point_configured(browser.get("close_tab_button"))

        ready_flags = [article_ready, scroll_ready, visible_ready, more_ready, copy_ready, tab_ready]
        if all(ready_flags):
            return "complete"
        if any(ready_flags):
            return "partial"
        if article_list.get("scroll_amount") == defaults["windows"]["article_list"]["scroll_amount"] and article_list.get("visible_articles") == defaults["windows"]["article_list"]["visible_articles"]:
            return "none"
        return "partial"

    def _get_dashboard_status_color(self, status, is_empty_content=False):
        """Return a dashboard-friendly color for article status."""
        if is_empty_content:
            return COLOR_WARNING
        if status == "scraped":
            return COLOR_SUCCESS
        if status == "failed":
            return COLOR_ERROR
        if status == "pending":
            return COLOR_WARNING
        return "gray"

    def _refresh_dashboard_todos(self, stats, is_calibrated):
        """Refresh the dashboard reminder block."""
        for child in self.dashboard_todo_container.winfo_children():
            child.destroy()

        reminders = []
        if not is_calibrated:
            reminders.append(("尚未完成坐标校准，请先完成坐标记录。", COLOR_WARNING))
        if stats["pending"] > 0:
            reminders.append((f"当前有 {stats['pending']} 篇待抓取文章，建议继续执行内容抓取。", COLOR_INFO))
        if stats["failed"] > 0:
            reminders.append((f"当前有 {stats['failed']} 篇抓取失败文章，建议检查后重新抓取。", COLOR_ERROR))
        if stats["empty_content"] > 0:
            reminders.append((f"当前有 {stats['empty_content']} 篇无内容文章，建议执行重抓。", COLOR_WARNING))

        if reminders:
            self.dashboard_todo_summary_label.config(text="当前有以下事项需要处理：", foreground=COLOR_PRIMARY_DARK)
        else:
            self.dashboard_todo_summary_label.config(text="当前状态良好，可以继续下一步工作。", foreground=COLOR_SUCCESS)
            reminders.append(("暂无待处理异常，采集环境已准备就绪。", COLOR_SUCCESS))

        for message, color in reminders:
            item_frame = ttk.Frame(self.dashboard_todo_container)
            item_frame.pack(fill=tk.X, pady=(0, SECTION_GAP_SMALL))
            ttk.Label(item_frame, text="•", foreground=color, font=FONT_TITLE).pack(side=tk.LEFT, anchor=tk.N)
            ttk.Label(
                item_frame,
                text=message,
                font=FONT_HELP_LARGE,
                foreground=color,
                justify=tk.LEFT,
                wraplength=320
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

    def _refresh_dashboard_recent_articles(self):
        """Refresh the recent-articles list on the dashboard."""
        for child in self.dashboard_recent_container.winfo_children():
            child.destroy()

        recent_articles = self.db.get_recent_articles(limit=5)
        if not recent_articles:
            ttk.Label(
                self.dashboard_recent_container,
                text="还没有文章记录。先完成链接采集后，这里会显示最近文章。",
                font=FONT_HELP_LARGE,
                foreground="gray"
            ).pack(anchor=tk.W, pady=(SECTION_GAP_SMALL, 0))
            return

        for index, (article_id, title, publish_time, status, is_empty_content) in enumerate(recent_articles):
            row_frame = ttk.Frame(self.dashboard_recent_container)
            row_frame.pack(fill=tk.X, pady=(0, SECTION_GAP_SMALL))
            row_frame.columnconfigure(0, weight=1)

            title_text = (title or "(无标题)")
            if len(title_text) > 48:
                title_text = title_text[:45] + "..."

            ttk.Label(
                row_frame,
                text=title_text,
                font=FONT_LABEL
            ).grid(row=0, column=0, sticky="w")

            ttk.Label(
                row_frame,
                text=publish_time or "发布时间未知",
                font=FONT_HELP,
                foreground="gray"
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))

            ttk.Label(
                row_frame,
                text=self._format_article_status(status, bool(is_empty_content)),
                font=FONT_HELP,
                foreground=self._get_dashboard_status_color(status, bool(is_empty_content))
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(SECTION_GAP, 0))

            if index < len(recent_articles) - 1:
                ttk.Separator(self.dashboard_recent_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, SECTION_GAP_SMALL))

    def _refresh_dashboard(self, stats):
        """Refresh dashboard-specific summary content."""
        self._refresh_dashboard_todos(stats, self._get_calibration_overall_state() == "complete")
        self._refresh_dashboard_recent_articles()

    def _update_statistics(self):
        """Update statistics on dashboard"""
        stats = self.db.get_statistics()
        calibration_state = self._get_calibration_overall_state()

        for key, label in self.stats_labels.items():
            label.config(text=str(stats[key]))

        self.last_update_label.config(
            text=f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        self._refresh_dashboard(stats)

        # Update calibration status
        if calibration_state == "complete":
            self.calibration_status_label.config(
                text="校准状态: 已校准",
                foreground=COLOR_SUCCESS
            )
        elif calibration_state == "partial":
            self.calibration_status_label.config(
                text="校准状态: 部分校准",
                foreground=COLOR_INFO
            )
        else:
            self.calibration_status_label.config(
                text="校准状态: 未校准",
                foreground=COLOR_WARNING
            )

        # Update scraping pending count
        self.scrape_pending_label.config(
            text=f"待抓取文章: {stats['pending']} 篇"
        )
        self.scrape_empty_label.config(
            text=f"无内容文章: {stats['empty_content']} 篇"
        )

        # Refresh article list if visible
        if self.notebook.select() == str(self.articles_tab):
            self._refresh_article_list()

        if self.calibration_item_widgets:
            self._refresh_calibration_items()

    def _update_scrape_result_labels(self, success=None, failed=None):
        """Update the per-run scrape result labels."""
        if success is not None:
            self.scrape_success_label.config(text=f"成功: {success}")
        if failed is not None:
            self.scrape_failed_label.config(text=f"失败: {failed}")

    def _schedule_article_layout_refresh(self, event=None):
        """Debounce article-list layout recalculation during window resize."""
        if not hasattr(self, "articles_tree"):
            return

        if event is not None and event.widget not in {self.root, self.articles_tree}:
            return

        if self.article_resize_after_id:
            self.root.after_cancel(self.article_resize_after_id)

        self.article_resize_after_id = self.root.after(30, self._resize_articles_columns)

    def _schedule_article_search_refresh(self, event=None):
        """Debounce article search refreshes while typing."""
        if self.article_search_after_id:
            self.root.after_cancel(self.article_search_after_id)

        self.article_search_after_id = self.root.after(300, self._reset_article_list_page)

    def _reset_article_list_page(self, event=None):
        """Reset article list pagination to the first page and refresh."""
        self.article_current_page = 1
        self._refresh_article_list()

    def _on_article_page_size_change(self, event=None):
        """Handle page size changes for the article list."""
        raw_value = self.article_page_size_var.get().strip()
        try:
            page_size = int(raw_value)
        except ValueError:
            self.article_page_size_var.set(str(self.article_page_size))
            return

        if page_size <= 0:
            self.article_page_size_var.set(str(self.article_page_size))
            return

        self.article_page_size = page_size
        self.article_page_size_var.set(str(page_size))
        self._reset_article_list_page()

    def _change_article_page(self, delta):
        """Move the article list to the previous or next page."""
        total_pages = max(1, (self.article_total_count + self.article_page_size - 1) // self.article_page_size)
        target_page = min(max(1, self.article_current_page + delta), total_pages)
        if target_page == self.article_current_page:
            return

        self.article_current_page = target_page
        self._refresh_article_list()

    def _update_article_pagination_controls(self, current_page_count):
        """Update pagination labels and button states."""
        total_pages = max(1, (self.article_total_count + self.article_page_size - 1) // self.article_page_size)
        current_page = min(self.article_current_page, total_pages)

        if hasattr(self, "article_page_info_label"):
            self.article_page_info_label.config(
                text=f"第 {current_page} / {total_pages} 页，共 {self.article_total_count} 篇，当前页 {current_page_count} 篇"
            )

        prev_state = tk.NORMAL if current_page > 1 else tk.DISABLED
        next_state = tk.NORMAL if current_page < total_pages else tk.DISABLED

        if hasattr(self, "article_prev_page_button"):
            self.article_prev_page_button.config(state=prev_state)
        if hasattr(self, "article_next_page_button"):
            self.article_next_page_button.config(state=next_state)

    def _resize_articles_columns(self, event=None):
        """Resize article columns to fit the current tree width."""
        if not hasattr(self, "articles_tree"):
            return

        self.article_resize_after_id = None

        tree_width = event.width if event and event.widget == self.articles_tree else self.articles_tree.winfo_width()
        if tree_width <= 1:
            return

        available_width = max(tree_width - 6, 320)

        checked_width = 64
        publish_width = min(150, max(96, int(available_width * 0.16)))
        status_width = min(104, max(72, int(available_width * 0.11)))

        flexible_width = max(160, available_width - checked_width - publish_width - status_width)
        title_width = max(90, int(flexible_width * 0.42))
        url_width = max(70, flexible_width - title_width)

        self.articles_tree.column("#0", width=checked_width)
        self.articles_tree.column("title", width=title_width)
        self.articles_tree.column("url", width=url_width)
        self.articles_tree.column("publish_time", width=publish_width)
        self.articles_tree.column("status", width=status_width)

    def _get_selected_article_ids(self):
        """Return article ids currently checked in the list."""
        return [article_id for article_id in self._get_visible_article_ids() if article_id in self.checked_article_ids]

    def _get_visible_article_ids(self):
        """Return article ids currently visible in the list."""
        article_ids = []
        for item in self.articles_tree.get_children():
            article_id = self._get_article_id_from_item(item)
            if article_id is not None:
                article_ids.append(article_id)
        return article_ids

    def _get_article_id_from_item(self, item):
        """Extract the article id stored in a tree item tag."""
        for tag in self.articles_tree.item(item).get("tags", ()):
            if isinstance(tag, int):
                return tag
            if isinstance(tag, str) and tag.isdigit():
                return int(tag)
        return None

    def _check_all_visible_articles(self, event=None):
        """Check all currently visible articles."""
        if not hasattr(self, "articles_tree"):
            return "break"

        self.checked_article_ids.update(self._get_visible_article_ids())
        self._refresh_article_checkboxes()
        return "break"

    def _clear_checked_articles(self, event=None):
        """Clear checked articles."""
        self.checked_article_ids.clear()
        self.article_check_anchor_id = None
        self._refresh_article_checkboxes()
        return "break"

    def _check_article_range(self, start_article_id, end_article_id):
        """Check all visible articles in the range between two article ids."""
        visible_ids = self._get_visible_article_ids()
        try:
            start_index = visible_ids.index(start_article_id)
            end_index = visible_ids.index(end_article_id)
        except ValueError:
            return False

        range_start, range_end = sorted((start_index, end_index))
        self.checked_article_ids.update(visible_ids[range_start:range_end + 1])
        return True

    def _on_articles_tree_click(self, event):
        """Handle row focus and checkbox toggling explicitly."""
        item = self.articles_tree.identify_row(event.y)
        if not item:
            return

        article_id = self._get_article_id_from_item(item)
        if article_id is None:
            return

        self.articles_tree.focus(item)
        self.articles_tree.selection_set(item)

        if event.state & 0x0001 and self.article_check_anchor_id is not None:
            if not self._check_article_range(self.article_check_anchor_id, article_id):
                self.checked_article_ids.add(article_id)
        else:
            if article_id in self.checked_article_ids:
                self.checked_article_ids.remove(article_id)
            else:
                self.checked_article_ids.add(article_id)

        self.article_check_anchor_id = article_id
        self._refresh_article_checkboxes()
        return "break"

    def _refresh_article_checkboxes(self):
        """Refresh checkbox display for visible rows."""
        if not hasattr(self, "articles_tree"):
            return

        for item in self.articles_tree.get_children():
            article_id = self._get_article_id_from_item(item)
            checkbox_image = (
                self.article_checked_image
                if article_id in self.checked_article_ids
                else self.article_unchecked_image
            )
            self.articles_tree.item(item, image=checkbox_image)

        self._update_article_selection_actions()

    def _toggle_article_sort(self, column):
        """Toggle article list sorting for the given column."""
        if self.article_sort_column == column:
            self.article_sort_descending = not self.article_sort_descending
        else:
            self.article_sort_column = column
            self.article_sort_descending = False

        self._update_article_sort_headings()
        self.article_current_page = 1
        self._refresh_article_list()

    def _update_article_sort_headings(self):
        """Update sortable article heading labels with direction indicators."""
        if not hasattr(self, "articles_tree"):
            return

        title_text = "标题"
        publish_time_text = "发布时间"

        if self.article_sort_column == "title":
            title_text += " ↓" if self.article_sort_descending else " ↑"
        elif self.article_sort_column == "publish_time":
            publish_time_text += " ↓" if self.article_sort_descending else " ↑"

        self.articles_tree.heading("title", text=title_text)
        self.articles_tree.heading("publish_time", text=publish_time_text)

    def _finalize_article_list_refresh(self, visible_article_ids):
        """Finalize selection state after the article list has been populated."""
        self.checked_article_ids.intersection_update(visible_article_ids)
        if self.article_check_anchor_id not in visible_article_ids:
            self.article_check_anchor_id = None
        self._update_article_pagination_controls(len(visible_article_ids))
        self._update_article_selection_actions()

    def _insert_article_rows_batch(self, articles, start_index, checked_ids, visible_article_ids, refresh_token):
        """Insert article rows in batches to keep the UI responsive."""
        if refresh_token != self.article_list_refresh_token:
            return

        batch = articles[start_index:start_index + self.ARTICLE_LIST_BATCH_SIZE]
        for article_id, url, title, publish_time, scraped_at, file_path, status, is_empty_content in batch:
            visible_article_ids.add(article_id)

            row_tags = (str(article_id),)
            if is_empty_content:
                row_tags += ("empty_content",)

            item_id = self.articles_tree.insert(
                "",
                tk.END,
                text="",
                image=(
                    self.article_checked_image
                    if article_id in checked_ids
                    else self.article_unchecked_image
                ),
                values=(
                    title or "(无标题)",
                    url or "",
                    publish_time or "N/A",
                    self._format_article_status(status, bool(is_empty_content))
                ),
                tags=row_tags
            )
            if not self.articles_tree.focus():
                self.articles_tree.focus(item_id)
                self.articles_tree.selection_set(item_id)

        next_index = start_index + len(batch)
        if next_index < len(articles):
            self.root.after(
                1,
                lambda: self._insert_article_rows_batch(
                    articles,
                    next_index,
                    checked_ids,
                    visible_article_ids,
                    refresh_token
                )
            )
            return

        self._finalize_article_list_refresh(visible_article_ids)

    def _update_article_selection_actions(self):
        """Update action button states based on current selection."""
        selected_count = len(self._get_selected_article_ids()) if hasattr(self, "articles_tree") else 0

        if hasattr(self, "article_selection_label"):
            self.article_selection_label.config(text=f"已勾选 {selected_count} 篇")

        has_selection = selected_count > 0

        if hasattr(self, "export_selected_button"):
            self.export_selected_button.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        if hasattr(self, "retry_selected_button"):
            self.retry_selected_button.config(state=tk.NORMAL if has_selection else tk.DISABLED)
        if hasattr(self, "delete_selected_button"):
            self.delete_selected_button.config(state=tk.NORMAL if has_selection else tk.DISABLED)
            label = "删除选中" if selected_count == 0 else f"删除选中 ({selected_count})"
            self.delete_selected_button.config(text=label)

    def _get_primary_article_id(self, preferred_item=None):
        """Return the primary article id for single-item actions."""
        candidate_items = []
        if preferred_item:
            candidate_items.append(preferred_item)

        focus_item = self.articles_tree.focus() if hasattr(self, "articles_tree") else ""
        if focus_item:
            candidate_items.append(focus_item)

        candidate_items.extend(self.articles_tree.selection() if hasattr(self, "articles_tree") else ())
        candidate_items.extend(self.articles_tree.get_children() if hasattr(self, "articles_tree") else ())

        seen = set()
        for item in candidate_items:
            if not item or item in seen:
                continue
            seen.add(item)
            article_id = self._get_article_id_from_item(item)
            if article_id is not None:
                if article_id in self.checked_article_ids or preferred_item or item == focus_item:
                    return article_id

        checked_ids = self._get_selected_article_ids()
        if checked_ids:
            return checked_ids[0]
        return None

    def _get_article_data(self, article_id):
        """Fetch full article data for a single article."""
        import sqlite3

        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, url, publish_time, scraped_at, status, file_path, content_html, content_markdown
            FROM articles WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'id': row[0],
            'title': row[1],
            'url': row[2],
            'publish_time': row[3],
            'scraped_at': row[4],
            'status': row[5],
            'file_path': row[6],
            'content_html': row[7],
            'content_markdown': row[8]
        }

    def _format_article_status(self, status, is_empty_content=False):
        """Return the display text for article status."""
        if is_empty_content:
            return "已抓取(无内容)"
        return status

    def _preview_selected_article(self, preferred_item=None):
        """Preview the selected article as Markdown text."""
        article_id = self._get_primary_article_id(preferred_item)
        if article_id is None:
            messagebox.showinfo("提示", "请先选择一篇文章")
            return

        article_data = self._get_article_data(article_id)
        if not article_data:
            messagebox.showwarning("提示", "未找到对应文章")
            return

        ArticlePreviewDialog(self.root, article_data).show()
        self._update_statistics()

    def _export_selected_article(self):
        """Export the selected article as a Markdown file."""
        article_id = self._get_primary_article_id()
        if article_id is None:
            messagebox.showinfo("提示", "请先选择一篇文章")
            return

        output_dir = filedialog.askdirectory(title="选择导出目录", parent=self.root)
        if not output_dir:
            return

        article_data = self._get_article_data(article_id)
        if not article_data:
            messagebox.showwarning("提示", "未找到对应文章")
            return

        try:
            export_path = self.file_store.export_markdown_article(article_data, output_dir)
        except ValueError as exc:
            messagebox.showwarning("无法导出", str(exc))
            return

        messagebox.showinfo("导出完成", f"已导出到:\n{export_path}")

    def _export_articles_batch(self):
        """Export selected articles, or the current list if nothing is selected."""
        article_ids = self._get_selected_article_ids() or self._get_visible_article_ids()
        if not article_ids:
            messagebox.showinfo("提示", "当前没有可导出的文章")
            return

        output_dir = filedialog.askdirectory(title="选择批量导出目录", parent=self.root)
        if not output_dir:
            return

        exported_paths = []
        skipped_titles = []

        for article_id in article_ids:
            article_data = self._get_article_data(article_id)
            if not article_data:
                continue

            try:
                exported_paths.append(
                    self.file_store.export_markdown_article(article_data, output_dir)
                )
            except ValueError:
                skipped_titles.append(article_data.get("title") or f"ID {article_id}")

        if not exported_paths:
            messagebox.showwarning("无法导出", "选中的文章都没有可用的 Markdown 内容")
            return

        message = f"已导出 {len(exported_paths)} 篇文章到:\n{output_dir}"
        if skipped_titles:
            message += f"\n\n跳过 {len(skipped_titles)} 篇无正文文章"
        messagebox.showinfo("批量导出完成", message)

    def _retry_selected_articles(self):
        """Retry only the currently selected articles."""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        article_ids = self._get_selected_article_ids()
        if not article_ids:
            messagebox.showinfo("提示", "请先选择要重新抓取的文章")
            return

        selected_articles = self.db.get_articles_by_ids(article_ids)
        if not selected_articles:
            messagebox.showwarning("提示", "未找到选中的文章")
            return

        count = len(selected_articles)
        if not messagebox.askyesno("确认", f"确定要重新抓取选中的 {count} 篇文章吗？"):
            return

        affected = self.db.reset_articles_by_ids(article_ids)
        if affected == 0:
            messagebox.showinfo("提示", "没有文章需要重新抓取")
            return

        self._update_statistics()
        self._start_scraping(
            pending_articles=selected_articles,
            intro_message=f"已将选中的 {affected} 篇文章重置为待抓取状态，开始重新抓取。"
        )

    def _delete_selected_articles(self):
        """Delete the currently selected articles and local backup files."""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        article_ids = self._get_selected_article_ids()
        if not article_ids:
            messagebox.showinfo("提示", "请先选择要删除的文章")
            return

        articles = []
        for article_id in article_ids:
            article_data = self._get_article_data(article_id)
            if article_data:
                articles.append(article_data)

        if not articles:
            messagebox.showwarning("提示", "未找到选中的文章")
            return

        count = len(articles)
        prompt = (
            f"确定要删除选中的 {count} 篇文章吗？\n\n"
            "这会同时删除数据库记录和本地 HTML/Markdown 备份文件。"
        )
        if not messagebox.askyesno("确认删除", prompt):
            return

        removed_files = 0
        file_errors = []
        for article_data in articles:
            try:
                removed_files += len(self.file_store.delete_article_files(article_data))
            except OSError as exc:
                file_errors.append(f"{article_data.get('title') or article_data['id']}: {exc}")

        deleted = self.db.delete_articles_by_ids(article_ids)
        self._update_statistics()

        message = f"已删除 {deleted} 篇文章"
        if removed_files:
            message += f"\n同时删除了 {removed_files} 个本地备份文件"
        if file_errors:
            message += f"\n\n有 {len(file_errors)} 篇文章的文件删除失败，请检查权限或文件状态。"
        messagebox.showinfo("删除完成", message)

    def _refresh_article_list(self):
        """Refresh the article list"""
        if self.article_search_after_id:
            self.root.after_cancel(self.article_search_after_id)
            self.article_search_after_id = None

        self.article_list_refresh_token += 1
        refresh_token = self.article_list_refresh_token
        checked_ids = set(self.checked_article_ids)
        visible_article_ids = set()

        # Clear existing items
        for item in self.articles_tree.get_children():
            self.articles_tree.delete(item)

        # Get filter and search
        status_filter = self.article_filter_var.get()
        search = self.article_search_var.get().strip()

        self.article_total_count = self.db.count_articles(status_filter, search=search)
        total_pages = max(1, (self.article_total_count + self.article_page_size - 1) // self.article_page_size)
        if self.article_current_page > total_pages:
            self.article_current_page = total_pages

        offset = (self.article_current_page - 1) * self.article_page_size

        # Get articles
        articles = self.db.get_articles_by_status(
            status_filter,
            search=search,
            sort_column=self.article_sort_column,
            descending=self.article_sort_descending,
            limit=self.article_page_size,
            offset=offset
        )
        if not articles:
            self._finalize_article_list_refresh(visible_article_ids)
            return

        self._insert_article_rows_batch(
            articles,
            0,
            checked_ids,
            visible_article_ids,
            refresh_token
        )

    def _on_article_double_click(self, event):
        """Handle double-click on article"""
        item = self.articles_tree.identify_row(event.y)
        if not item:
            return

        self.articles_tree.focus(item)
        self.articles_tree.selection_set(item)
        self._preview_selected_article(preferred_item=item)

    def _start_collection(self):
        """Start link collection"""
        if self.calibration_active_item:
            messagebox.showinfo("提示", "当前有进行中的校准项，请先完成或取消后再开始采集")
            return

        # Check calibration
        if not get_coordinates_path().exists():
            messagebox.showwarning(
                "提示",
                "尚未完成坐标校准。\n\n请先到“坐标校准”页面完成校准。"
            )
            return

        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        # Switch to collection tab
        self.notebook.select(self.collection_tab)

        # Clear log
        self.collect_log.delete(1.0, tk.END)
        self.collect_progress['value'] = 0
        self.collect_log.insert(tk.END, "提示: 运行过程中可点击“停止”或按 Esc 停止任务。\n\n")

        # Create worker
        self.current_worker = LinkCollectorWorker()
        self.current_worker.start()

        # Update UI
        self.collect_button.config(state=tk.DISABLED)
        self.collect_stop_button.config(state=tk.NORMAL)

        # Start checking signals
        self._check_worker_signals()

    def _start_test(self):
        """Start calibration test"""
        self.notebook.select(self.calibration_tab)

        if self.calibration_active_item:
            messagebox.showinfo("提示", "当前有进行中的校准项，请先完成或取消后再测试")
            return

        # Check calibration
        if not get_coordinates_path().exists():
            messagebox.showwarning(
                "提示",
                "尚未完成坐标校准。\n\n请先到“坐标校准”页面完成校准。"
            )
            return

        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        def pause_callback(prompt):
            return self._call_on_ui_thread(
                lambda: True if messagebox.askokcancel("测试坐标", prompt, parent=self.root) else None
            )

        def confirm_callback(prompt):
            return self._call_on_ui_thread(
                lambda: messagebox.askyesno("测试坐标", prompt, parent=self.root)
            )

        # Create worker
        self.current_worker = TestWorker(pause_callback, confirm_callback)
        self.current_worker.start()

        # Update UI
        self.test_button.config(state=tk.DISABLED)
        self.collect_button.config(state=tk.DISABLED)

        # Start checking signals
        self._check_worker_signals()

    def _start_scraping(self, pending_articles=None, intro_message=None):
        """Start content scraping"""
        if self.calibration_active_item:
            messagebox.showinfo("提示", "当前有进行中的校准项，请先完成或取消后再开始抓取")
            return

        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        pending = pending_articles if pending_articles is not None else self.db.get_pending_articles()
        if not pending:
            messagebox.showinfo("提示", "没有待抓取的文章")
            return

        # Switch to scraping tab
        self.notebook.select(self.scraping_tab)

        # Clear log
        self.scrape_log.delete(1.0, tk.END)
        self.scrape_progress['value'] = 0
        self.scrape_success_label.config(text="成功: 0")
        self.scrape_failed_label.config(text="失败: 0")
        self.scrape_log.insert(tk.END, "提示: 运行过程中可点击“停止”或按 Esc 停止任务。\n\n")
        if intro_message:
            self.scrape_log.insert(tk.END, intro_message + "\n\n")

        # Create worker
        self.current_worker = ContentScraperWorker(pending_articles=pending)
        self.current_worker.start()

        # Update UI
        self.scrape_button.config(state=tk.DISABLED)
        self.scrape_stop_button.config(state=tk.NORMAL)

        # Start checking signals
        self._check_worker_signals()

    def _stop_worker(self):
        """Stop the current worker"""
        if not self.current_worker or not self.current_worker.is_alive():
            return

        self.is_stopping = True
        self.current_worker.stop()
        self.worker_status_label.config(text=STATUS_STOPPING)

        # Add log message about stopping
        if isinstance(self.current_worker, (LinkCollectorWorker, TestWorker)):
            self.collect_log.insert(tk.END, "\n正在停止...\n")
            self.collect_log.see(tk.END)
        elif isinstance(self.current_worker, ContentScraperWorker):
            self.scrape_log.insert(tk.END, "\n正在停止...\n")
            self.scrape_log.see(tk.END)

        # Disable all buttons
        self.collect_button.config(state=tk.DISABLED)
        self.collect_stop_button.config(state=tk.DISABLED)
        self.scrape_button.config(state=tk.DISABLED)
        self.scrape_stop_button.config(state=tk.DISABLED)

        # Wait for worker to stop (with timeout)
        start_wait_time = time.time()
        MAX_WAIT_TIME = 10  # Maximum 10 seconds to stop

        def wait_for_stop():
            # Check if worker completed normally (via signals)
            if not self.is_stopping and self.current_worker is None:
                return  # Worker completed, nothing to do

            # Check timeout
            if time.time() - start_wait_time > MAX_WAIT_TIME:
                self.worker_status_label.config(text="停止超时")
                self.is_stopping = False
                self._reset_start_buttons()
                return

            if self.current_worker and self.current_worker.is_alive():
                # Keep checking
                self.worker_timer = self.root.after(100, wait_for_stop)
            else:
                # Worker has stopped but complete signal wasn't received (edge case)
                self.is_stopping = False
                self._reset_start_buttons()

        wait_for_stop()

    def _handle_escape_stop(self, event=None):
        """Handle Esc key as a stop signal for active tasks."""
        if self.calibration_active_item:
            self._cancel_active_calibration_action()
            return
        if not self.current_worker or not self.current_worker.is_alive() or self.is_stopping:
            return
        self._stop_worker()

    def _reset_start_buttons(self):
        """Reset start buttons to normal state after stop completes"""
        self.collect_button.config(state=tk.NORMAL)
        self.collect_stop_button.config(state=tk.DISABLED)
        self.scrape_button.config(state=tk.NORMAL)
        self.scrape_stop_button.config(state=tk.DISABLED)
        self._set_calibration_buttons_state(bool(self.calibration_active_item))

    def _check_worker_signals(self):
        """Check for signals from worker"""
        if not self.current_worker:
            return

        # Process all pending signals (not just one)
        max_signals_per_check = 20  # Limit to prevent infinite loop
        signals_processed = 0

        while signals_processed < max_signals_per_check:
            signal = self.current_worker.signals.get(timeout=0.005)

            if not signal:
                break  # No more signals in queue

            signals_processed += 1
            signal_type, data = signal

            if signal_type == 'log':
                # Determine which log to use
                if isinstance(self.current_worker, (LinkCollectorWorker, TestWorker)):
                    self.collect_log.insert(tk.END, data['message'] + '\n')
                    self.collect_log.see(tk.END)
                elif isinstance(self.current_worker, ContentScraperWorker):
                    self.scrape_log.insert(tk.END, data['message'] + '\n')
                    self.scrape_log.see(tk.END)

            elif signal_type == 'progress':
                current = data['current']
                total = data['total']
                message = data.get('message', '')

                if isinstance(self.current_worker, LinkCollectorWorker):
                    self.collect_progress['value'] = (current / total * 100) if total > 0 else 0
                    self.collect_status_label.config(
                        text=message or f"已采集 {current} 篇"
                    )
                elif isinstance(self.current_worker, ContentScraperWorker):
                    self.scrape_progress['value'] = (current / total * 100) if total > 0 else 0
                    self.scrape_status_label.config(
                        text=message or f"已抓取 {current}/{total} 篇"
                    )
                    self._update_scrape_result_labels(
                        success=data.get('success'),
                        failed=data.get('failed'),
                    )

            elif signal_type == 'status':
                self.worker_status_label.config(text=data['status'])

            elif signal_type == 'error':
                messagebox.showerror("错误", data['message'])
                self.worker_status_label.config(text=STATUS_ERROR)

            elif signal_type == 'complete':
                self._worker_complete(data)
                return  # Stop checking after complete

        # Continue checking if worker is still alive
        if self.current_worker and self.current_worker.is_alive():
            self.root.after(50, self._check_worker_signals)

    def _worker_complete(self, data):
        """Handle worker completion"""
        # Clear the worker reference first to prevent issues
        worker = self.current_worker
        self.current_worker = None

        # Update status based on whether we were stopping
        if self.is_stopping:
            self.worker_status_label.config(text="已停止")
            self.is_stopping = False
        elif data.get('cancelled'):
            self.worker_status_label.config(text="已取消")
        elif data.get('passed') is False:
            self.worker_status_label.config(text="未通过")
        else:
            self.worker_status_label.config(text=STATUS_DONE)

        self._update_statistics()

        if isinstance(worker, ContentScraperWorker):
            self._update_scrape_result_labels(
                success=data.get('success', 0),
                failed=data.get('failed', 0),
            )

        # Reset buttons immediately (don't wait for message box)
        self._reset_start_buttons()

        # Show completion message using after() to avoid blocking signal processing
        self.root.after(100, lambda: self._show_completion_message(data))

        # Cancel any pending wait_for_stop timers
        if self.worker_timer:
            try:
                self.root.after_cancel(self.worker_timer)
            except:
                pass
            self.worker_timer = None

    def _show_completion_message(self, data):
        """Show completion message (non-blocking)"""
        if data.get('cancelled'):
            messagebox.showinfo("完成", "操作已取消")
        elif data.get('passed') is False:
            messagebox.showwarning("完成", "测试未通过，请重新校准")
        elif data.get('passed') is True and 'count' not in data and 'success' not in data and 'failed' not in data:
            messagebox.showinfo("完成", "测试通过")
        elif data.get('stopped'):
            messagebox.showinfo("完成", "操作已停止")
        else:
            message = "操作完成！"
            if 'count' in data:
                message += f"\n处理: {data['count']} 篇"
            if 'success' in data:
                message += f"\n成功: {data['success']} 篇"
            if 'failed' in data:
                message += f"\n失败: {data['failed']} 篇"
            messagebox.showinfo("完成", message)

    def _retry_failed(self):
        """Retry failed articles"""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        stats = self.db.get_statistics()
        if stats['failed'] == 0:
            messagebox.showinfo("提示", "没有失败的文章需要重试")
            return

        if messagebox.askyesno("确认", f"确定要重试 {stats['failed']} 篇失败的文章吗？"):
            self.current_worker = RetryFailedWorker()
            self.current_worker.start()
            self._check_worker_signals()

    def _retry_empty_articles(self):
        """Retry articles that were scraped without content."""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        empty_articles = self.db.get_empty_content_articles()
        if not empty_articles:
            messagebox.showinfo("提示", "没有无内容文章需要重新抓取")
            return

        count = len(empty_articles)
        if not messagebox.askyesno("确认", f"确定要重新抓取 {count} 篇无内容文章吗？"):
            return

        affected = self.db.reset_empty_content()
        if affected == 0:
            messagebox.showinfo("提示", "没有无内容文章需要重新抓取")
            return

        pending_articles = [(article_id, url) for article_id, url in empty_articles]
        self._update_statistics()
        self._start_scraping(
            pending_articles=pending_articles,
            intro_message=f"已将 {affected} 篇无内容文章重置为待抓取状态，开始重新抓取。"
        )

    def _generate_index(self):
        """Generate article index"""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        self.current_worker = GenerateIndexWorker()
        self.current_worker.start()
        self._check_worker_signals()

    def _open_calibration(self):
        """Navigate to the calibration tab and refresh the page state."""
        self.notebook.select(self.calibration_tab)
        self._refresh_calibration_items()

    def _open_articles_dir(self):
        """Open articles directory"""
        articles_dir = self.file_store.base_dir
        if articles_dir.exists():
            webbrowser.open(str(articles_dir))
        else:
            messagebox.showinfo("提示", "文章目录不存在")

    def _open_data_dir(self):
        """Open data directory"""
        data_dir = self.db.db_path.parent
        if data_dir.exists():
            webbrowser.open(str(data_dir))
        else:
            messagebox.showinfo("提示", "数据目录不存在")

    def _export_data_bundle(self):
        """Export the runtime database and article backups as one zip archive."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"wechat-scraper-data-{timestamp}.zip"
        output_path = filedialog.asksaveasfilename(
            title="导出数据包",
            parent=self.root,
            defaultextension=".zip",
            initialfile=default_name,
            filetypes=[("ZIP archive", "*.zip")],
        )
        if not output_path:
            return

        try:
            result = export_data_bundle(output_path)
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))
            return

        messagebox.showinfo(
            "导出完成",
            f"已导出到:\n{result.archive_path}\n\n共打包 {result.file_count} 个文件。",
        )

    def _import_database(self):
        """Import an external database file and replace the runtime database."""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        source_path = filedialog.askopenfilename(
            title="选择要导入的数据库文件",
            parent=self.root,
            filetypes=[("SQLite database", "*.db"), ("All files", "*.*")],
        )
        if not source_path:
            return

        confirmed = messagebox.askyesno(
            "确认导入数据库",
            "导入会替换当前运行时数据库，并先创建一个本地备份。\n\n"
            "注意：这只会替换数据库文件，不会同步 HTML/Markdown 备份目录，"
            "导入后数据库记录与本地备份文件可能不一致。\n\n"
            "是否继续？",
        )
        if not confirmed:
            return

        try:
            result = import_database_file(source_path, target_db_path=self.db.db_path)
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))
            return

        self.db = Database(self.db.db_path)
        self.checked_article_ids.clear()
        self.article_check_anchor_id = None
        self.article_current_page = 1
        self._update_statistics()
        if hasattr(self, "articles_tree"):
            self._refresh_article_list()

        message = f"已导入数据库:\n{result.source_db_path}"
        if result.backup_path:
            message += f"\n\n原数据库已备份到:\n{result.backup_path}"
        messagebox.showinfo("导入完成", message)

    def _show_about(self):
        """Show about dialog"""
        about_text = """
微信公众号文章采集工具 v1.0

功能特点:
- 三步流程：坐标校准 → 链接采集 → 内容抓取
- 链接采集：通过自动化采集公众号文章链接
- 内容抓取：提取文章正文并转换为Markdown
- 进度追踪：实时显示采集和抓取进度
- 内容预览：双击查看文章Markdown内容

作者：Claude
        """
        messagebox.showinfo("关于", about_text)

    def run(self):
        """Run the GUI application"""
        # Update stats periodically
        self.root.after(5000, self._periodic_update)

        # Start the main loop
        self.root.mainloop()

    def _periodic_update(self):
        """Periodically update statistics"""
        if not self.current_worker or not self.current_worker.is_alive():
            self._update_statistics()
        self.root.after(5000, self._periodic_update)


if __name__ == "__main__":
    app = WeChatScraperGUI()
    app.run()
