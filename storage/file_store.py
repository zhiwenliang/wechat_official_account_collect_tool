"""
文件存储模块
将文章内容保存为HTML和Markdown格式
"""
from pathlib import Path
from datetime import datetime
import re

class FileStore:
    def __init__(self, base_dir="data/articles"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, title):
        """清理文件名中的非法字符"""
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        return title[:100]

    def save_article(self, article_data):
        """保存文章到文件"""
        title = article_data['title']
        publish_time = article_data.get('publish_time', '')

        # 按月份组织目录
        try:
            date_obj = datetime.fromisoformat(publish_time)
            folder = date_obj.strftime('%Y-%m')
        except:
            folder = 'unknown'

        article_dir = self.base_dir / folder
        article_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        safe_title = self._sanitize_filename(title)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{safe_title}"

        # 保存HTML
        html_path = article_dir / f"{filename}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_html(article_data))

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
