"""
UI Styling Constants for the GUI
"""

# Colors
COLOR_PRIMARY = "#2E7D32"      # Green
COLOR_PRIMARY_DARK = "#1B5E20"  # Dark Green
COLOR_ACCENT = "#4CAF50"        # Light Green
COLOR_WARNING = "#FF9800"      # Orange
COLOR_ERROR = "#F44336"        # Red
COLOR_SUCCESS = "#4CAF50"      # Green
COLOR_INFO = "#2196F3"         # Blue

# Background Colors
BG_DASHBOARD = "#F5F5F5"
BG_ARTICLE_SCAPED = "#E8F5E9"
BG_ARTICLE_FAILED = "#FFEBEE"
BG_ARTICLE_PENDING = "#FFF3E0"

# Fonts
FONT_HEADER = ("Helvetica", 16, "bold")
FONT_TITLE = ("Helvetica", 14, "bold")
FONT_LABEL = ("Helvetica", 11)
FONT_BUTTON = ("Helvetica", 10)
FONT_LOG = ("Consolas", 9)

# Sizes
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
LOG_HEIGHT = 150

# Tab names
TAB_DASHBOARD = "仪表盘"
TAB_COLLECTION = "链接采集"
TAB_SCRAPING = "内容抓取"
TAB_ARTICLES = "文章管理"
TAB_CALIBRATION = "坐标校准"

# Status messages
STATUS_IDLE = "就绪"
STATUS_WORKING = "工作中..."
STATUS_STOPPING = "正在停止..."
STATUS_DONE = "完成"
STATUS_ERROR = "错误"

# Progress messages
PROGRESS_COLLECTING = "正在采集链接: {current}/{total}"
PROGRESS_SCRAPING = "正在抓取文章: {current}/{total}"
PROGRESS_CALIBRATING = "校准进度: {step}/{total} - {description}"
