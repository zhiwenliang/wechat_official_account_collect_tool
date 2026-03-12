"""
Main GUI Application for WeChat Official Account Scraper
Provides a user-friendly interface for link collection and content scraping
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import webbrowser
import os
import time
from pathlib import Path
from datetime import datetime

from storage.database import Database
from gui.worker import (
    WorkerSignals, LinkCollectorWorker, ContentScraperWorker,
    RetryFailedWorker, GenerateIndexWorker, CalibrationWorker, TestWorker
)
from gui.preview_dialog import ArticlePreviewDialog
from gui.styles import *


class WeChatScraperGUI:
    """Main GUI Application"""

    def __init__(self):
        """Initialize the GUI application"""
        self.root = tk.Tk()
        self.root.title("微信公众号文章采集工具")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Database
        self.db = Database()

        # Current worker
        self.current_worker = None
        self.worker_timer = None
        self.is_stopping = False  # Track if we're in the middle of stopping

        # Calibration position tracking
        self.calibration_position = None
        self.calibration_waiting = False
        self.calibration_callback = None

        self._setup_ui()
        self._update_statistics()

    def _setup_ui(self):
        """Setup the main UI"""
        # Create menu bar
        self._create_menu()

        # Create main notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.dashboard_tab = self._create_dashboard_tab()
        self.collection_tab = self._create_collection_tab()
        self.scraping_tab = self._create_scraping_tab()
        self.articles_tab = self._create_articles_tab()
        self.calibration_tab = self._create_calibration_tab()

        # Status bar
        self._create_status_bar()

    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开文章目录", command=self._open_articles_dir)
        file_menu.add_command(label="打开数据库位置", command=self._open_data_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="重新抓取失败文章", command=self._retry_failed)
        tools_menu.add_command(label="生成文章索引", command=self._generate_index)
        tools_menu.add_separator()
        tools_menu.add_command(label="刷新统计", command=self._update_statistics)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)

    def _create_dashboard_tab(self):
        """Create the dashboard tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=TAB_DASHBOARD)

        # Header
        header = ttk.Frame(frame, padding=20)
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="微信公众号文章采集工具",
            font=("Helvetica", 20, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            header,
            text="两步采集公众号文章内容：链接采集 → 内容抓取",
            font=("Helvetica", 10),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        # Statistics cards
        stats_frame = ttk.Frame(frame, padding=20)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        # Stats grid
        self.stats_labels = {}

        stats_info = [
            ("total", "总文章数", COLOR_PRIMARY),
            ("pending", "待抓取", COLOR_WARNING),
            ("scraped", "已抓取", COLOR_SUCCESS),
            ("failed", "抓取失败", COLOR_ERROR)
        ]

        for i, (key, label, color) in enumerate(stats_info):
            card_frame = ttk.LabelFrame(stats_frame, text=label, padding=20)
            card_frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

            value_label = ttk.Label(
                card_frame,
                text="0",
                font=("Helvetica", 24, "bold"),
                foreground=color
            )
            value_label.pack()

            self.stats_labels[key] = value_label

        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)

        # Quick actions
        actions_frame = ttk.LabelFrame(frame, text="快捷操作", padding=20)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)

        # Action buttons
        actions = [
            ("开始链接采集", self._start_collection, COLOR_PRIMARY),
            ("开始内容抓取", self._start_scraping, COLOR_ACCENT),
            ("重新抓取失败文章", self._retry_failed, COLOR_WARNING),
            ("生成文章索引", self._generate_index, COLOR_INFO)
        ]

        for i, (text, command, color) in enumerate(actions):
            btn = tk.Button(
                actions_frame,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Helvetica", 11, "bold"),
                relief=tk.FLAT,
                padx=20,
                pady=10
            )
            btn.grid(row=0, column=i, padx=10, pady=10, sticky="ew")

        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        actions_frame.columnconfigure(2, weight=1)
        actions_frame.columnconfigure(3, weight=1)

        # Last update
        self.last_update_label = ttk.Label(
            frame,
            text="",
            font=("Helvetica", 8),
            foreground="gray"
        )
        self.last_update_label.pack(pady=5)

        return frame

    def _create_collection_tab(self):
        """Create the link collection tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=TAB_COLLECTION)

        # Control frame
        control_frame = ttk.Frame(frame, padding=20)
        control_frame.pack(fill=tk.X)

        # Calibration status
        self.calibration_status_label = ttk.Label(
            control_frame,
            text="校准状态: 未校准",
            font=("Helvetica", 10, "bold"),
            foreground=COLOR_WARNING
        )
        self.calibration_status_label.pack(anchor=tk.W)

        ttk.Button(
            control_frame,
            text="打开坐标校准向导",
            command=self._open_calibration
        ).pack(anchor=tk.W, pady=5)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

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

        self.test_button = ttk.Button(
            control_frame,
            text="测试坐标",
            command=self._start_test
        )
        self.test_button.pack(side=tk.LEFT)

        # Preparation checklist
        checklist_frame = ttk.LabelFrame(frame, text="准备工作检查", padding=15)
        checklist_frame.pack(fill=tk.X, padx=20, pady=10)

        checklist_items = [
            "窗口1：已打开公众号页面，并点击【文章分组】，滚动到页面最顶部",
            "窗口2：已打开微信内置浏览器",
            "两个窗口不重叠且都可见",
            "已完成坐标校准"
        ]

        for item in checklist_items:
            ttk.Label(checklist_frame, text=f"  {item}", font=("Helvetica", 9)).pack(anchor=tk.W)

        # Progress frame
        progress_frame = ttk.Frame(frame, padding=20)
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
        log_frame = ttk.LabelFrame(frame, text="采集日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.collect_log = scrolledtext.ScrolledText(
            log_frame,
            height=LOG_HEIGHT,
            font=FONT_LOG,
            wrap=tk.WORD
        )
        self.collect_log.pack(fill=tk.BOTH, expand=True)

        return frame

    def _create_scraping_tab(self):
        """Create the content scraping tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=TAB_SCRAPING)

        # Control frame
        control_frame = ttk.Frame(frame, padding=20)
        control_frame.pack(fill=tk.X)

        # Pending count
        self.scrape_pending_label = ttk.Label(
            control_frame,
            text="待抓取文章: 0 篇",
            font=("Helvetica", 10, "bold")
        )
        self.scrape_pending_label.pack(anchor=tk.W)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

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

        # Counters
        counters_frame = ttk.Frame(control_frame)
        counters_frame.pack(side=tk.RIGHT)

        self.scrape_success_label = ttk.Label(counters_frame, text="成功: 0", foreground=COLOR_SUCCESS)
        self.scrape_success_label.pack(side=tk.LEFT, padx=10)

        self.scrape_failed_label = ttk.Label(counters_frame, text="失败: 0", foreground=COLOR_ERROR)
        self.scrape_failed_label.pack(side=tk.LEFT, padx=10)

        # Progress frame
        progress_frame = ttk.Frame(frame, padding=20)
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
        log_frame = ttk.LabelFrame(frame, text="抓取日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.scrape_log = scrolledtext.ScrolledText(
            log_frame,
            height=LOG_HEIGHT,
            font=FONT_LOG,
            wrap=tk.WORD
        )
        self.scrape_log.pack(fill=tk.BOTH, expand=True)

        return frame

    def _create_articles_tab(self):
        """Create the articles management tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=TAB_ARTICLES)

        # Control frame
        control_frame = ttk.Frame(frame, padding=20)
        control_frame.pack(fill=tk.X)

        # Filter
        ttk.Label(control_frame, text="状态筛选:").pack(side=tk.LEFT)

        self.article_filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            control_frame,
            textvariable=self.article_filter_var,
            values=["all", "pending", "scraped", "failed"],
            state="readonly",
            width=10
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self._refresh_article_list)

        # Search
        ttk.Label(control_frame, text="搜索:").pack(side=tk.LEFT, padx=(20, 5))

        self.article_search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.article_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_article_list())

        # Buttons
        ttk.Button(
            control_frame,
            text="刷新列表",
            command=self._refresh_article_list
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            control_frame,
            text="重新抓取失败文章",
            command=self._retry_failed
        ).pack(side=tk.LEFT, padx=5)

        # Treeview for articles
        tree_frame = ttk.Frame(frame, padding=10)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Treeview with scrollbar
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.articles_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "title", "url", "publish_time", "status"),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )

        tree_scroll_y.config(command=self.articles_tree.yview)
        tree_scroll_x.config(command=self.articles_tree.xview)

        self.articles_tree.heading("id", text="ID")
        self.articles_tree.heading("title", text="标题")
        self.articles_tree.heading("url", text="链接")
        self.articles_tree.heading("publish_time", text="发布时间")
        self.articles_tree.heading("status", text="状态")

        self.articles_tree.column("id", width=50)
        self.articles_tree.column("title", width=400)
        self.articles_tree.column("url", width=380)
        self.articles_tree.column("publish_time", width=150)
        self.articles_tree.column("status", width=80)

        self.articles_tree.bind("<Double-1>", self._on_article_double_click)

        self.articles_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        return frame

    def _create_calibration_tab(self):
        """Create the calibration wizard tab"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=TAB_CALIBRATION)

        # Instructions
        instructions_frame = ttk.Frame(frame, padding=20)
        instructions_frame.pack(fill=tk.X)

        ttk.Label(
            instructions_frame,
            text="坐标校准向导",
            font=("Helvetica", 16, "bold")
        ).pack(anchor=tk.W)

        ttk.Label(
            instructions_frame,
            text="按照以下步骤完成坐标校准，确保采集功能正常工作",
            font=("Helvetica", 10),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(5, 0))

        ttk.Separator(instructions_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Start button
        self.calibrate_button = ttk.Button(
            instructions_frame,
            text="开始校准",
            command=self._start_calibration
        )
        self.calibrate_button.pack(anchor=tk.W)

        # Live calibration progress (shown on the page)
        progress_frame = ttk.Frame(frame, padding=(20, 0, 20, 10))
        progress_frame.pack(fill=tk.X)

        ttk.Label(progress_frame, text="当前校准进度:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W)

        self.calibration_progress = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            maximum=100
        )
        self.calibration_progress.pack(fill=tk.X, pady=5)

        self.calibration_progress_label = ttk.Label(
            progress_frame,
            text="未开始",
            font=("Helvetica", 9),
            foreground="gray"
        )
        self.calibration_progress_label.pack(anchor=tk.W)

        # Calibration info
        info_frame = ttk.LabelFrame(frame, text="校准说明", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        info_text = """
坐标校准是采集功能正常运行的关键步骤。校准过程需要：

1. 测量文章行高：定位两篇相邻文章的顶部位置
2. 定位文章底部：确定第一篇文章的底部位置
3. 测试滚动单位：确定每次滚动移动的像素距离
4. 定位更多按钮：记录微信浏览器的"更多"按钮位置
5. 定位复制链接菜单：确认(Enter)后会倒计时10秒，期间打开更多菜单并将鼠标停在"复制链接"上
6. 定位标签管理：程序会自动点击文章20次打开标签，再记录第一个标签和关闭按钮位置

操作技巧（避免记录到弹窗按钮坐标）：
- 把鼠标移动到目标位置后，尽量用键盘 Enter 确认
- 如需先在微信里点击（如打开“更多”菜单），把鼠标停在目标点后，用 Alt+Tab/Cmd+Tab 切回弹窗，再按 Enter

注意事项：
- 校准后请勿移动微信窗口的位置和大小
- 如窗口位置改变，需要重新校准
- 建议在两个窗口都不重叠的情况下进行校准
"""
        ttk.Label(info_frame, text=info_text, font=("Helvetica", 9), justify=tk.LEFT).pack(anchor=tk.W)

        return frame

    def _create_status_bar(self):
        """Create the status bar"""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(10, 5))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT)

        self.status_label = ttk.Label(status_frame, text=STATUS_IDLE)
        self.status_label.pack(side=tk.LEFT, padx=5)

        ttk.Separator(status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)

        self.worker_status_label = ttk.Label(status_frame, text="")
        self.worker_status_label.pack(side=tk.LEFT)

    def _update_statistics(self):
        """Update statistics on dashboard"""
        stats = self.db.get_statistics()

        for key, label in self.stats_labels.items():
            label.config(text=str(stats[key]))

        self.last_update_label.config(
            text=f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Update calibration status
        config_path = Path("config/coordinates.json")
        if config_path.exists():
            self.calibration_status_label.config(
                text="校准状态: 已校准",
                foreground=COLOR_SUCCESS
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

        # Refresh article list if visible
        if self.notebook.index(self.notebook.select()) == 3:  # Articles tab
            self._refresh_article_list()

    def _refresh_article_list(self):
        """Refresh the article list"""
        # Clear existing items
        for item in self.articles_tree.get_children():
            self.articles_tree.delete(item)

        # Get filter and search
        status_filter = self.article_filter_var.get()
        search = self.article_search_var.get().lower()

        # Get articles
        articles = self.db.get_articles_by_status(status_filter)

        # Add to treeview
        for article_id, url, title, publish_time, scraped_at, file_path, status in articles:
            # Apply search filter
            if search and search not in (title or "").lower() and search not in (url or "").lower():
                continue

            # Insert into treeview
            self.articles_tree.insert(
                "",
                tk.END,
                values=(
                    article_id,
                    title or "(无标题)",
                    url or "",
                    publish_time or "N/A",
                    status
                ),
                tags=(article_id,)
            )

    def _on_article_double_click(self, event):
        """Handle double-click on article"""
        selection = self.articles_tree.selection()
        if not selection:
            return

        # Get article data from database
        article_id = self.articles_tree.item(selection[0])['values'][0]

        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, url, publish_time, scraped_at, status, file_path, content_html, content_markdown
            FROM articles WHERE id = ?
        """, (article_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            article_data = {
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

            ArticlePreviewDialog(self.root, article_data).show()
            self._update_statistics()

    def _start_collection(self):
        """Start link collection"""
        # Check calibration
        if not Path("config/coordinates.json").exists():
            messagebox.showwarning(
                "提示",
                "尚未完成坐标校准。\n\n请先点击'打开坐标校准向导'完成校准。"
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
        # Check calibration
        if not Path("config/coordinates.json").exists():
            messagebox.showwarning(
                "提示",
                "尚未完成坐标校准。\n\n请先点击'打开坐标校准向导'完成校准。"
            )
            return

        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        # Create worker
        self.current_worker = TestWorker()
        self.current_worker.start()

        # Update UI
        self.test_button.config(state=tk.DISABLED)
        self.collect_button.config(state=tk.DISABLED)

        # Start checking signals
        self._check_worker_signals()

    def _start_scraping(self):
        """Start content scraping"""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        pending = self.db.get_pending_articles()
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

        # Create worker
        self.current_worker = ContentScraperWorker()
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
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:  # Collection tab
            self.collect_log.insert(tk.END, "\n正在停止...\n")
            self.collect_log.see(tk.END)
        elif current_tab == 2:  # Scraping tab
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

    def _reset_start_buttons(self):
        """Reset start buttons to normal state after stop completes"""
        self.collect_button.config(state=tk.NORMAL)
        self.collect_stop_button.config(state=tk.DISABLED)
        self.scrape_button.config(state=tk.NORMAL)
        self.scrape_stop_button.config(state=tk.DISABLED)
        self.test_button.config(state=tk.NORMAL)

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
                        text=message or f"已采集 {current}/{total} 篇"
                    )
                elif isinstance(self.current_worker, ContentScraperWorker):
                    self.scrape_progress['value'] = (current / total * 100) if total > 0 else 0
                    self.scrape_status_label.config(
                        text=message or f"已抓取 {current}/{total} 篇"
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
        else:
            self.worker_status_label.config(text=STATUS_DONE)

        self._update_statistics()

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
        if data.get('stopped'):
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

    def _generate_index(self):
        """Generate article index"""
        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行")
            return

        self.current_worker = GenerateIndexWorker()
        self.current_worker.start()
        self._check_worker_signals()

    def _open_calibration(self):
        """Navigate to calibration tab (does not start calibration)."""
        self.notebook.select(self.calibration_tab)

    def _start_calibration(self):
        """Start calibration wizard from the calibration tab."""
        self.notebook.select(self.calibration_tab)

        if self.current_worker and self.current_worker.is_alive():
            messagebox.showinfo("提示", "已有任务正在运行，请先等待当前任务完成")
            return

        if messagebox.askyesno("确认", "开始坐标校准？\n\n请确保微信窗口已准备好。"):
            # Reset on-page progress UI
            if hasattr(self, "calibration_progress"):
                self.calibration_progress["value"] = 0
            if hasattr(self, "calibration_progress_label"):
                self.calibration_progress_label.config(text="准备开始...", foreground="gray")
            self._run_calibration_wizard()

    def _run_calibration_wizard(self):
        """Run the calibration wizard"""
        import pyautogui

        # Reset state
        self.calibration_waiting = True
        self.calibration_position = None

        # Create worker
        def step_callback(prompt):
            """Callback for calibration steps"""
            # Wait for user to click
            self.calibration_waiting = True
            self.calibration_position = None

            result = messagebox.askokcancel(
                "坐标校准",
                f"{prompt}\n\n确认后将记录当前鼠标位置（建议按 Enter 确认）"
            )

            self.calibration_waiting = False

            if result:
                return pyautogui.position()
            return None

        worker = CalibrationWorker(step_callback)
        worker.start()

        # Poll worker signals so we can show a completion dialog (calibration has its own flow)
        self.worker_status_label.config(text="校准中...")
        max_signals_per_check = 50

        def poll_signals():
            signals_processed = 0
            while signals_processed < max_signals_per_check:
                signal = worker.signals.get(timeout=0.001)
                if not signal:
                    break

                signals_processed += 1
                signal_type, data = signal

                if signal_type == "status":
                    self.worker_status_label.config(text=data.get("status", ""))
                elif signal_type == "progress":
                    # Show progress in status bar (no dedicated calibration log UI)
                    step = data.get("current", 0)
                    total = data.get("total", 0)
                    desc = data.get("message", "")
                    progress_text = PROGRESS_CALIBRATING.format(step=step, total=total, description=desc)
                    self.worker_status_label.config(text=progress_text)

                    # Also show on calibration tab
                    if hasattr(self, "calibration_progress") and total:
                        self.calibration_progress["value"] = (step / total) * 100
                    if hasattr(self, "calibration_progress_label"):
                        self.calibration_progress_label.config(text=progress_text, foreground="gray")
                elif signal_type == "error":
                    self.calibration_waiting = False
                    self.worker_status_label.config(text=STATUS_ERROR)
                    self._update_statistics()
                    if hasattr(self, "calibration_progress_label"):
                        self.calibration_progress_label.config(text="校准失败", foreground=COLOR_ERROR)
                    messagebox.showerror("校准失败", data.get("message", "校准失败"))
                    return
                elif signal_type == "complete":
                    self.calibration_waiting = False
                    if data.get("cancelled"):
                        self.worker_status_label.config(text="已取消")
                        self._update_statistics()
                        if hasattr(self, "calibration_progress_label"):
                            self.calibration_progress_label.config(text="已取消", foreground=COLOR_WARNING)
                        messagebox.showinfo("已取消", "坐标校准已取消。")
                        return

                    self.worker_status_label.config(text=STATUS_DONE)
                    self._update_statistics()
                    saved_path = data.get("path") or "config/coordinates.json"
                    if hasattr(self, "calibration_progress"):
                        self.calibration_progress["value"] = 100
                    if hasattr(self, "calibration_progress_label"):
                        self.calibration_progress_label.config(text="校准完成", foreground=COLOR_SUCCESS)
                    messagebox.showinfo(
                        "校准完成",
                        f"坐标校准已完成。\n\n已保存到: {saved_path}\n\n建议点击“测试坐标”确认效果。"
                    )
                    return

            if worker.is_alive():
                self.root.after(100, poll_signals)
            else:
                # Worker ended without emitting complete/error (unexpected)
                self.calibration_waiting = False
                self._update_statistics()
                self.worker_status_label.config(text=STATUS_DONE)
                messagebox.showinfo(
                    "校准结束",
                    "校准流程已结束。\n\n请检查是否生成了 config/coordinates.json，并点击“测试坐标”确认效果。"
                )

        poll_signals()

    def _open_articles_dir(self):
        """Open articles directory"""
        articles_dir = Path("data/articles")
        if articles_dir.exists():
            webbrowser.open(str(articles_dir))
        else:
            messagebox.showinfo("提示", "文章目录不存在")

    def _open_data_dir(self):
        """Open data directory"""
        data_dir = Path("data")
        if data_dir.exists():
            webbrowser.open(str(data_dir))
        else:
            messagebox.showinfo("提示", "数据目录不存在")

    def _show_about(self):
        """Show about dialog"""
        about_text = """
微信公众号文章采集工具 v1.0

功能特点:
- 链接采集：通过自动化采集公众号文章链接
- 内容抓取：提取文章正文并转换为Markdown
- 进度追踪：实时显示采集和抓取进度
- 内容预览：查看文章的HTML和Markdown内容

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
