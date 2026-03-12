"""
Article Content Preview Dialog
Allows viewing Markdown content of articles
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests
from PIL import Image, ImageTk

from storage.file_store import FileStore


class ArticlePreviewDialog:
    """Dialog for previewing article content"""

    IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\(([^)]+)\)')

    def __init__(self, parent, article_data):
        """
        Initialize the preview dialog

        Args:
            parent: Parent window
            article_data: Dictionary with keys: id, title, url, publish_time, scraped_at,
                          status, content_html, content_markdown, file_path
        """
        self.article_data = article_data
        self.file_store = FileStore()
        self.preview_images = []
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

        try:
            word_count = len(self.file_store.get_markdown_content(self.article_data))
        except ValueError:
            word_count = 0
        ttk.Label(status_frame, text=f"  |  字数: {word_count}").pack(side=tk.LEFT)

    def _load_content(self):
        """Load Markdown content for preview."""
        try:
            content = self.file_store.get_markdown_content(self.article_data)
        except ValueError:
            content = ""

        if not content:
            content = "(无内容)"

        self.preview_images = []
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self._render_markdown_content(content)
        self.text_widget.config(state=tk.DISABLED)

    def _render_markdown_content(self, content):
        """Render Markdown text and inline image previews."""
        for line in content.splitlines():
            self.text_widget.insert(tk.END, f"{line}\n")
            image_matches = list(self.IMAGE_PATTERN.finditer(line))
            for match in image_matches:
                alt_text = match.group(1).strip()
                image_url = self._extract_image_url(match.group(2))
                self._insert_image_preview(image_url, alt_text)

    def _extract_image_url(self, raw_target):
        """Extract the actual image URL/path from a Markdown image target."""
        target = raw_target.strip().strip("<>").strip()
        if " " in target:
            target = target.split(" ", 1)[0]
        return target

    def _insert_image_preview(self, image_url, alt_text):
        """Insert one image preview into the text widget."""
        self.text_widget.insert(tk.END, "\n")
        try:
            image_bytes = self._read_image_bytes(image_url)
            pil_image = Image.open(BytesIO(image_bytes))
            pil_image.load()

            max_width = max(320, self.text_widget.winfo_width() - 60)
            if max_width <= 320:
                max_width = 760
            pil_image.thumbnail((max_width, 480))

            tk_image = ImageTk.PhotoImage(pil_image)
            self.preview_images.append(tk_image)
            self.text_widget.image_create(tk.END, image=tk_image)

            caption = alt_text or Path(urlparse(image_url).path).name or "图片"
            self.text_widget.insert(tk.END, f"\n[图片] {caption}\n\n")
        except Exception as exc:
            fallback = alt_text or "未命名图片"
            self.text_widget.insert(
                tk.END,
                f"[图片加载失败] {fallback}\n{image_url}\n{exc}\n\n"
            )

    def _read_image_bytes(self, image_url):
        """Read image bytes from a remote URL or local path."""
        parsed = urlparse(image_url)

        if parsed.scheme in {"http", "https"}:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            return response.content

        if parsed.scheme == "file":
            return Path(unquote(parsed.path)).read_bytes()

        local_path = Path(image_url)
        if local_path.is_absolute() and local_path.exists():
            return local_path.read_bytes()

        candidate_paths = []
        file_path = self.article_data.get("file_path")
        if file_path:
            article_dir = Path(file_path).resolve().parent
            candidate_paths.append(article_dir / image_url)
            candidate_paths.append(article_dir.parent / image_url)
        candidate_paths.append(Path.cwd() / image_url)

        for candidate in candidate_paths:
            if candidate.exists():
                return candidate.read_bytes()

        raise FileNotFoundError(f"找不到图片: {image_url}")

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
