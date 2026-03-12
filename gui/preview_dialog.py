"""
Article Content Preview Dialog
Allows viewing HTML and Markdown content of articles
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import os
from pathlib import Path
from html.parser import HTMLParser
import re


class HTMLToTextParser(HTMLParser):
    """Simple HTML to text converter for preview"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True
        elif tag == 'p':
            self.text.append('\n')
        elif tag == 'br':
            self.text.append('\n')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.text.append('\n' + '#' * int(tag[1]) + ' ')

    def handle_endtag(self, tag):
        if tag == 'body':
            self.in_body = False
        elif tag == 'p':
            self.text.append('\n')

    def handle_data(self, data):
        if self.in_body:
            self.text.append(data)

    def get_text(self):
        return ''.join(self.text)


class ArticlePreviewDialog:
    """Dialog for previewing article content"""

    def __init__(self, parent, article_data):
        """
        Initialize the preview dialog

        Args:
            parent: Parent window
            article_data: Dictionary with keys: id, title, url, publish_time, scraped_at,
                          status, content_html, content_markdown, file_path
        """
        self.article_data = article_data
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"文章预览 - {article_data.get('title', '无标题')[:30]}")
        self.dialog.geometry("900x700")

        # Make dialog modal-like (still can interact with parent if desired)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()
        self._load_content()

    def _setup_ui(self):
        """Setup the dialog UI"""
        # Header frame
        header_frame = ttk.Frame(self.dialog, padding=10)
        header_frame.pack(fill=tk.X)

        # Title
        title_label = ttk.Label(
            header_frame,
            text=self.article_data.get('title', '无标题'),
            font=("Helvetica", 14, "bold")
        )
        title_label.pack(anchor=tk.W)

        # Metadata
        meta_frame = ttk.Frame(header_frame)
        meta_frame.pack(fill=tk.X, pady=(5, 0))

        # Publish time
        publish_time = self.article_data.get('publish_time', 'N/A')
        ttk.Label(meta_frame, text=f"发布时间: {publish_time}").pack(side=tk.LEFT)

        # URL
        url = self.article_data.get('url', '')
        url_label = ttk.Label(
            meta_frame,
            text=f"链接: {url[:60]}..." if len(url) > 60 else f"链接: {url}",
            foreground="blue"
        )
        url_label.pack(side=tk.LEFT, padx=(20, 0))
        url_label.bind("<Button-1>", lambda e: webbrowser.open(url))

        # Button frame
        button_frame = ttk.Frame(self.dialog, padding=(10, 5))
        button_frame.pack(fill=tk.X)

        # View type selector
        ttk.Label(button_frame, text="查看方式:").pack(side=tk.LEFT)

        self.view_var = tk.StringVar(value="markdown")
        view_combo = ttk.Combobox(
            button_frame,
            textvariable=self.view_var,
            values=["markdown", "html"],
            state="readonly",
            width=10
        )
        view_combo.pack(side=tk.LEFT, padx=(5, 20))
        view_combo.bind("<<ComboboxSelected>>", self._on_view_change)

        # Action buttons
        ttk.Button(
            button_frame,
            text="在浏览器中打开",
            command=self._open_in_browser
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="打开文件",
            command=self._open_file
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="关闭",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT)

        # Content frame
        content_frame = ttk.Frame(self.dialog, padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget for preview
        self.text_widget = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # Status bar
        status_frame = ttk.Frame(self.dialog, padding=(10, 5))
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(
            status_frame,
            text=f"状态: {self.article_data.get('status', 'unknown')}"
        )
        self.status_label.pack(side=tk.LEFT)

        word_count = len(self.article_data.get('content_markdown', ''))
        ttk.Label(status_frame, text=f"  |  字数: {word_count}").pack(side=tk.LEFT)

    def _load_content(self):
        """Load content based on selected view type"""
        view_type = self.view_var.get()
        content = ""

        if view_type == "markdown":
            content = self.article_data.get('content_markdown', '')
            if not content and self.article_data.get('content_html'):
                # Fallback: convert HTML to Markdown
                parser = HTMLToTextParser()
                parser.feed(self.article_data['content_html'])
                content = parser.get_text()
        else:  # html
            content = self._clean_html_for_preview(
                self.article_data.get('content_html', '')
            )

        if not content:
            content = "(无内容)"

        # Display content
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, content)

    def _clean_html_for_preview(self, html_content):
        """Clean HTML content for text preview"""
        # Extract text content
        parser = HTMLToTextParser()
        parser.feed(html_content)
        return parser.get_text()

    def _on_view_change(self, event=None):
        """Handle view type change"""
        self._load_content()

    def _open_in_browser(self):
        """Open article in browser"""
        url = self.article_data.get('url', '')
        if url:
            webbrowser.open(url)
        else:
            messagebox.showwarning("提示", "没有有效的文章链接")

    def _open_file(self):
        """Open article file in default application"""
        file_path = self.article_data.get('file_path', '')
        if not file_path:
            # Try to construct file path from URL
            url = self.article_data.get('url', '')
            if url:
                messagebox.showinfo("提示", f"文章链接: {url}\n\n文件尚未保存")
            return

        if os.path.exists(file_path):
            # Open with default application
            os.startfile(file_path) if os.name == 'nt' else os.system(f'open "{file_path}"')
        else:
            messagebox.showwarning("提示", f"文件不存在: {file_path}")

    def show(self):
        """Show the dialog and wait"""
        self.dialog.wait_window()
