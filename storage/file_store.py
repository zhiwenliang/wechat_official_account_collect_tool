"""
文件存储模块
将文章内容保存为HTML和Markdown格式
"""
from pathlib import Path
from datetime import datetime
from markdownify import markdownify as md
import re

class FileStore:
    def __init__(self, base_dir="data/articles"):
        self.base_dir = Path(base_dir)
        self.html_dir = self.base_dir / "html"
        self.md_dir = self.base_dir / "markdown"

        # 创建目录
        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.md_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, title):
        """清理文件名中的非法字符"""
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        return title[:100]

    def generate_index(self):
        """生成文章目录索引"""
        articles = []

        # 遍历markdown目录下的所有Markdown文件
        for md_file in sorted(self.md_dir.glob('*.md'), reverse=True):
            # 解析文件名：YYYYMMDD_HHMMSS_标题.md
            filename = md_file.stem
            parts = filename.split('_', 2)

            if len(parts) >= 3:
                date_str = parts[0]  # YYYYMMDD
                time_str = parts[1]  # HHMMSS
                title = parts[2]

                # 格式化日期时间
                try:
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    formatted_date = date_str

                articles.append({
                    'date': formatted_date,
                    'title': title,
                    'filename': md_file.name
                })

        # 生成索引文件到markdown目录
        index_path = self.md_dir / 'INDEX.md'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write('# 文章目录索引\n\n')
            f.write(f'> 共 {len(articles)} 篇文章\n\n')

            for article in articles:
                f.write(f"- **{article['date']}** - [{article['title']}]({article['filename']})\n")

        return str(index_path)

    def save_article(self, article_data):
        """保存文章到文件"""
        title = article_data['title']
        publish_time = article_data.get('publish_time', '')

        # 使用发布时间作为文件名前缀
        try:
            date_obj = datetime.fromisoformat(publish_time)
            timestamp = date_obj.strftime('%Y%m%d_%H%M%S')
        except:
            # 如果发布时间解析失败，使用当前时间
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 生成文件名（使用发布时间）
        safe_title = self._sanitize_filename(title)
        filename = f"{timestamp}_{safe_title}"

        # 保存HTML到html目录
        html_path = self.html_dir / f"{filename}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_html(article_data))

        # 保存Markdown到markdown目录
        md_path = self.md_dir / f"{filename}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown(article_data))

        return str(html_path)

    def _generate_html(self, article_data):
        """生成完整的HTML文件"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{article_data['title']}</title>
    <style>
        body {{ max-width: 800px; margin: 0 auto; padding: 20px; font-family: sans-serif; }}
        .meta {{ color: #888; margin: 20px 0; }}
        #js_content {{ line-height: 1.6; }}
        img {{ max-width: 100%; }}
    </style>
</head>
<body>
    <h1>{article_data['title']}</h1>
    <div class="meta">
        <p>发布时间: {article_data.get('publish_time', 'N/A')}</p>
        <p>链接: <a href="{article_data['url']}">{article_data['url']}</a></p>
    </div>
    <div id="js_content">
        {article_data['content_html']}
    </div>
</body>
</html>"""
        return html

    def _generate_markdown(self, article_data):
        """生成Markdown文件"""
        # 转换HTML内容为Markdown
        content_md = md(article_data['content_html'], heading_style="ATX")

        # 生成完整的Markdown文档
        markdown = f"""# {article_data['title']}

**发布时间**: {article_data.get('publish_time', 'N/A')}
**原文链接**: {article_data['url']}

---

{content_md}
"""
        return markdown
