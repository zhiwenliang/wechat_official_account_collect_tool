"""
Article preview dialog showing raw Markdown or raw HTML content.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext

from gui.styles import FONT_HELP, FONT_LOG, FONT_TITLE, PAGE_PAD, SECTION_GAP, SECTION_GAP_SMALL
from storage.file_store import FileStore


class ArticlePreviewDialog:
    """Display raw article content without rendering."""

    VIEW_MARKDOWN = "Markdown"
    VIEW_HTML = "HTML"

    def __init__(self, parent, article_data):
        self.parent = parent
        self.article_data = article_data
        self.file_store = FileStore()

        self.window = None
        self.markdown_text = None
        self.html_text = None

    def show(self):
        """Open the preview dialog."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title(f"文章预览 - {self.article_data.get('title') or '无标题'}")
        self.window.geometry("920x720")
        self.window.transient(self.parent)
        self.window.grab_set()

        self._build_ui()
        self._load_content()

        self.window.focus_force()
        self.window.bind("<Escape>", lambda _event: self.window.destroy())
        self.window.wait_window()

    def _build_ui(self):
        """Create the dialog layout."""
        root = ttk.Frame(self.window, padding=PAGE_PAD)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=self.article_data.get("title") or "无标题",
            font=FONT_TITLE,
        ).grid(row=0, column=0, sticky="w")

        meta_lines = [
            f"发布时间: {self.article_data.get('publish_time') or 'N/A'}",
            f"状态: {self._format_status()}",
            f"链接: {self.article_data.get('url') or 'N/A'}",
        ]
        ttk.Label(
            header,
            text="\n".join(meta_lines),
            font=FONT_HELP,
            justify=tk.LEFT,
        ).grid(row=1, column=0, sticky="w", pady=(SECTION_GAP_SMALL, 0))

        controls = ttk.Frame(root)
        controls.grid(row=1, column=0, sticky="ew", pady=(SECTION_GAP, SECTION_GAP_SMALL))
        controls.columnconfigure(1, weight=1)

        ttk.Label(
            controls,
            text="仅展示文本内容，不做渲染",
            font=FONT_HELP,
            foreground="gray",
        ).grid(row=0, column=0, sticky="w")

        notebook = ttk.Notebook(root)
        notebook.grid(row=2, column=0, sticky="nsew")

        markdown_frame = ttk.Frame(notebook)
        html_frame = ttk.Frame(notebook)
        markdown_frame.columnconfigure(0, weight=1)
        markdown_frame.rowconfigure(0, weight=1)
        html_frame.columnconfigure(0, weight=1)
        html_frame.rowconfigure(0, weight=1)

        notebook.add(markdown_frame, text=self.VIEW_MARKDOWN)
        notebook.add(html_frame, text=self.VIEW_HTML)

        self.markdown_text = scrolledtext.ScrolledText(
            markdown_frame,
            wrap=tk.WORD,
            font=FONT_LOG,
            undo=False,
        )
        self.markdown_text.grid(row=0, column=0, sticky="nsew")

        self.html_text = scrolledtext.ScrolledText(
            html_frame,
            wrap=tk.WORD,
            font=FONT_LOG,
            undo=False,
        )
        self.html_text.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(root)
        footer.grid(row=3, column=0, sticky="e", pady=(SECTION_GAP_SMALL, 0))
        ttk.Button(footer, text="关闭", command=self.window.destroy).pack(side=tk.RIGHT)

    def _load_content(self):
        """Load raw Markdown and HTML content into their tabs."""
        if not self.markdown_text or not self.html_text:
            return

        self._set_text_content(self.markdown_text, self._get_raw_markdown())
        self._set_text_content(self.html_text, self._get_raw_html())

    def _set_text_content(self, widget, content):
        """Replace the content of one text widget."""
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.mark_set("insert", "1.0")

    def _get_raw_markdown(self):
        """Return raw Markdown content for the article."""
        try:
            content = self.file_store.get_markdown_content(self.article_data)
        except Exception:
            content = ""

        content = (content or "").strip()
        return content or "(无 Markdown 内容)"

    def _get_raw_html(self):
        """Return raw HTML content for the article."""
        content = (self.article_data.get("content_html") or "").strip()
        return content or "(无 HTML 内容)"

    def _format_status(self):
        """Return preview status text."""
        status = self.article_data.get("status") or "unknown"
        if status == "scraped" and not (self.article_data.get("content_html") or "").strip():
            return "已抓取(无内容)"
        return status
