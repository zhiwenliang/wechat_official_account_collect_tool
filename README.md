# 微信公众号历史文章采集工具

自动化采集微信公众号历史文章的工具，包含链接采集和内容抓取两个阶段。

## 功能特性

- 通过微信PC客户端采集文章链接
- 使用Playwright抓取文章详细内容
- SQLite数据库存储 + 本地文件备份
- 支持增量更新和断点续传

## 技术栈

- Python 3.8+
- pyautogui: 控制鼠标键盘
- pyperclip: 剪贴板操作
- playwright: 浏览器自动化
- sqlite3: 数据存储

## 环境配置

### 使用Conda创建专用环境

```bash
# 创建新的conda环境（Python 3.8+）
conda create -n wechat-scraper python=3.10

# 激活环境
conda activate wechat-scraper

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

后续使用时，只需激活环境：
```bash
conda activate wechat-scraper
```

如果需要删除环境：
```bash
conda remove -n wechat-scraper --all
```

## 使用流程

### 阶段1：采集文章链接

1. 打开微信PC客户端
2. 左侧窗口：打开目标公众号页面
3. 右侧窗口：打开微信内置浏览器（可以先随便点击一篇文章）
4. 调整两个窗口位置，确保不重叠且都可见
5. 运行坐标校准工具，记录关键位置
6. 运行链接采集脚本

### 阶段2：抓取文章内容

1. 运行内容抓取脚本
2. 自动访问已采集的链接
3. 提取标题、时间、阅读量、正文
4. 保存到数据库和本地文件

## 项目结构

```
wechat-article-scraper/
├── config/
│   └── coordinates.json    # 坐标配置
├── scraper/
│   ├── link_collector.py   # 链接采集
│   ├── content_scraper.py  # 内容抓取
│   └── calibrator.py       # 坐标校准工具
├── storage/
│   ├── database.py         # 数据库操作
│   └── file_store.py       # 文件存储
├── data/
│   ├── articles.db         # SQLite数据库
│   ├── links.txt           # 采集的链接列表
│   └── articles/           # 文章备份目录
├── requirements.txt
└── main.py
```
