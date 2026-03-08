# 微信公众号历史文章采集工具

自动化采集微信公众号历史文章的工具，包含链接采集和内容抓取两个阶段。

## 功能特性

- **阶段1**：通过微信PC客户端自动采集文章链接
  - 智能到底检测（连续5次重复+刷新确认）
  - 连续失败保护机制
  - 自动清理浏览器标签
  - Windows/macOS自动适配

- **阶段2**：使用Playwright抓取文章详细内容
  - 自动滚动加载所有懒加载图片
  - 中文时间格式解析
  - 同时保存HTML和Markdown格式
  - SQLite数据库存储 + 本地文件备份
  - 按月份组织文件

## 技术栈

- Python 3.8+
- pyautogui: 控制鼠标键盘
- pyperclip: 剪贴板操作
- playwright: 浏览器自动化
- markdownify: HTML转Markdown
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

## 快速开始

### 完整工作流程

```bash
# 1. 校准坐标（首次使用必须）
python main.py calibrate

# 2. 测试校准结果（可选）
python main.py test

# 3. 采集链接（需要手动准备微信窗口）
python main.py collect

# 4. 导入链接到数据库
python main.py import

# 5. 抓取文章内容
python main.py scrape
```

### 查看数据库状态

```bash
sqlite3 data/articles.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"
```

## 使用说明

### 阶段1：采集文章链接

**准备工作**：
1. 打开微信PC客户端
2. 窗口1：打开目标公众号页面，点击【文章分组】，滚动到页面最顶部
3. 窗口2：打开微信内置浏览器（可以先随便点击一篇文章）
4. 调整两个窗口位置，确保不重叠且都可见

**校准坐标**：
```bash
python main.py calibrate
```
按照提示依次标记：
- 文章行高
- 滚动单位
- 更多按钮
- 复制链接菜单
- 标签管理按钮

**开始采集**：
```bash
python main.py collect
```
- 采集过程中不要移动鼠标或操作电脑
- 鼠标移到屏幕角落可紧急停止
- 链接保存到 `data/links.txt`

### 阶段2：抓取文章内容

**导入链接**：
```bash
python main.py import
```

**抓取内容**：
```bash
python main.py scrape
```
- 自动访问所有待抓取的链接
- 提取标题、发布时间、正文HTML
- 自动滚动加载所有图片
- 同时保存HTML和Markdown格式
- 文件按月份组织：`data/articles/YYYY-MM/`

## 项目结构

```
wechat_official_account_collect_tool/
├── config/
│   └── coordinates.json      # 坐标配置文件
├── scraper/
│   ├── calibrator.py         # 坐标校准工具
│   ├── link_collector.py     # 链接采集模块
│   └── content_scraper.py    # 内容抓取模块
├── storage/
│   ├── database.py           # SQLite数据库操作
│   └── file_store.py         # 文件存储（HTML + Markdown）
├── data/
│   ├── articles.db           # SQLite数据库
│   ├── links.txt             # 采集的链接列表
│   └── articles/             # 文章备份目录（按月份）
│       └── YYYY-MM/
│           ├── *.html        # HTML格式
│           └── *.md          # Markdown格式
├── test_stage1.py            # 阶段1测试脚本
├── test_stage2.py            # 阶段2测试脚本
├── requirements.txt          # Python依赖
├── main.py                   # 主入口
├── CLAUDE.md                 # 项目文档（给AI用）
└── README.md                 # 本文件
```

## 注意事项

- 坐标校准后窗口位置不能变动
- 采集过程中不要移动鼠标或操作电脑
- 连续5次相同链接时会先刷新页面再确认到底
- 每30篇文章自动清理浏览器标签
- 滚动后等待2秒，确保页面加载完成
- Windows和macOS窗口激活机制不同，程序会自动适配

## 数据库结构

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE NOT NULL,
    publish_time TEXT,
    scraped_at TEXT,
    status TEXT DEFAULT 'pending',  -- pending/scraped/failed
    file_path TEXT
);
```

## 常见问题

**Q: 校准后采集失败？**
A: 确保窗口位置没有变动，可以运行 `python main.py test` 测试校准结果

**Q: 如何修改最大采集数量？**
A: 编辑 `config/coordinates.json` 中的 `collection.max_articles` 字段

**Q: 图片链接无法访问？**
A: 微信文章图片有防盗链，需要带referer下载

## 许可证

MIT License
