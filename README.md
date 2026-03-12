# 微信公众号历史文章采集工具

用于批量采集微信公众号历史文章的本地工具，分为两个阶段：

1. Stage 1：通过微信 PC 客户端自动采集文章链接
2. Stage 2：通过 Playwright 抓取文章正文，并保存到 SQLite 与本地文件

项目同时提供 CLI 和 Tkinter GUI，两者共用同一套工作流、数据库与导出目录。

## 功能概览

- Stage 1 链接采集
  - 基于 `pyautogui` + 剪贴板操作微信桌面端
  - 首次使用需要坐标校准
  - 连续重复链接检测，支持刷新确认是否到达底部
  - 连续失败保护
  - 每采集 30 篇自动清理标签页
  - 保留鼠标移到屏幕角落的 failsafe

- Stage 2 内容抓取
  - 基于 Playwright 抓取微信文章页面
  - 自动滚动以触发懒加载内容
  - 抽取标题、发布时间、正文 HTML
  - 同时保存 HTML 与 Markdown
  - 写入 SQLite，支持断点续传
  - 生成 `INDEX.md` 文章索引

- GUI 能力
  - 仪表盘查看采集状态
  - 图形化校准、测试、采集、抓取
  - 文章列表筛选、搜索、预览
  - 可重试失败文章或“已抓取但正文为空”的文章

## 环境要求

- Python 3.8+
- 已安装微信 PC 客户端
- Stage 2 需要安装 Playwright Chromium

## 安装

推荐使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

如果你使用 Conda，也可以：

```bash
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper
pip install -r requirements.txt
playwright install chromium
```

## 快速开始

典型 CLI 流程：

```bash
python main.py calibrate   # 首次使用必做
python main.py test        # 可选，验证校准
python main.py collect     # 采集文章链接到 SQLite
python main.py scrape      # 抓取正文并导出 HTML/Markdown
python main.py stats       # 查看统计信息
python main.py retry       # 将 failed 重置为 pending
python main.py index       # 重新生成 Markdown 索引
```

启动 GUI：

```bash
python -m gui.main
```

## CLI 命令说明

`python main.py` 支持以下命令：

- `calibrate`：记录 Stage 1 所需的屏幕坐标
- `test`：测试当前校准是否可用
- `collect`：采集公众号文章链接并写入数据库
- `scrape`：抓取所有 `pending` 文章正文
- `stats`：查看 `pending/scraped/failed/empty_content` 统计
- `retry`：把 `failed` 文章重置为 `pending`
- `index`：重新生成 `data/articles/markdown/INDEX.md`

## 使用流程

### 1. 坐标校准

首次运行必须执行：

```bash
python main.py calibrate
```

当前版本会记录 8 个关键项，包括：

- 文章列表行高
- 文章点击区域
- 滚动单位
- 可见文章数量
- 浏览器“更多”按钮
- “复制链接”菜单项
- 第一个标签页位置
- 关闭标签按钮位置

校准结果保存到 `config/coordinates.json`。

### 2. 链接采集

采集前请准备两个微信窗口：

1. 公众号文章列表窗口，点击“文章分组”并滚动到最顶部
2. 微信内置浏览器窗口，任意打开一篇文章即可

然后执行：

```bash
python main.py collect
```

注意：

- 采集过程中不要移动鼠标或手动操作微信窗口
- 坐标校准后，窗口位置和大小不要变化
- 鼠标移到屏幕角落会触发 `pyautogui` failsafe

### 3. 内容抓取

```bash
python main.py scrape
```

抓取阶段会：

- 读取数据库中 `pending` 文章
- 抓取正文 HTML 并转换 Markdown
- 将内容写回数据库
- 保存本地 HTML/Markdown 文件
- 完成后自动生成 Markdown 索引

如果中途中断，重新运行 `python main.py scrape` 即可继续。

## GUI 说明

GUI 入口：

```bash
python -m gui.main
```

GUI 包含以下区域：

- 仪表盘：查看总数、待抓取、已抓取、失败、无内容文章提示
- 校准页：执行图形化校准和校准测试
- 采集页：启动 Stage 1 链接采集
- 抓取页：启动 Stage 2 内容抓取
- 文章页：分页浏览、搜索、预览、批量重抓或删除

GUI “工具”菜单额外提供：

- 重新抓取失败文章
- 重新抓取无内容文章
- 重新生成文章索引

## 数据目录

运行时数据默认写入以下位置：

```text
config/coordinates.json
data/articles.db
data/articles/html/*.html
data/articles/markdown/*.md
data/articles/markdown/INDEX.md
```

文件名格式默认类似：

```text
YYYYMMDD_HHMMSS_文章标题.md
YYYYMMDD_HHMMSS_文章标题.html
```

## 项目结构

```text
wechat_official_account_collect_tool/
├── main.py
├── README.md
├── AGENTS.md
├── requirements.txt
├── scraper/
│   ├── calibrator.py
│   ├── link_collector.py
│   └── content_scraper.py
├── services/
│   ├── calibration_service.py
│   └── workflows.py
├── storage/
│   ├── database.py
│   └── file_store.py
├── gui/
│   ├── main.py
│   ├── app.py
│   ├── worker.py
│   ├── preview_dialog.py
│   └── styles.py
├── utils/
│   ├── escape_listener.py
│   ├── runtime_env.py
│   └── stop_control.py
├── scripts/
│   └── package_app.py
├── test_stage1.py
└── test_stage2.py
```

## 数据库说明

当前 `articles` 表核心字段如下：

```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    url TEXT UNIQUE NOT NULL,
    publish_time TEXT,
    scraped_at TEXT,
    status TEXT DEFAULT 'pending',
    file_path TEXT,
    content_html TEXT,
    content_markdown TEXT
);
```

状态说明：

- `pending`：等待抓取
- `scraped`：已抓取
- `failed`：抓取失败

额外约定：

- “无内容文章”不是单独状态，而是 `status='scraped'` 且 `content_html` 为空
- `retry` 只会重置 `failed`
- GUI 还支持重置“无内容文章”为 `pending`

## 打包可执行程序

项目提供 PyInstaller 打包脚本：

```bash
pip install pyinstaller
python scripts/package_app.py
python scripts/package_app.py --target gui
python scripts/package_app.py --target cli
python scripts/package_app.py --target gui --onefile
```

说明：

- 默认输出到 `dist/<platform-tag>/`
- 需要在目标平台本机打包，不能跨平台直接生成
- 打包前应先执行 `playwright install chromium`
- 打包脚本会把 `ms-playwright` 浏览器目录复制到运行产物旁边
- 打包后的程序会自动尝试发现旁边的 `ms-playwright` 目录

## 测试与检查

当前仓库没有接入独立测试框架，主要依赖手动脚本：

```bash
python main.py test
python test_stage1.py
python test_stage2.py
```

这些脚本带有真实 UI / 浏览器副作用，不适合直接作为 CI 自动化测试。

## 常见问题

**1. 校准后仍然采集失败？**

先运行：

```bash
python main.py test
```

如果测试异常，通常是微信窗口位置、缩放比例或布局发生了变化，需要重新校准。

**2. `scrape` 显示没有待抓取文章？**

先运行：

```bash
python main.py stats
```

确认数据库中是否已有 `pending` 记录。

**3. 已抓取但正文为空怎么办？**

CLI 只能查看统计；GUI 提供“重新抓取无内容文章”入口，可把这些记录重置回 `pending` 后重新抓取。

**4. 能否修改最大采集数量？**

可以，编辑 `config/coordinates.json` 中的 `collection.max_articles`。

## 安全与注意事项

- 不要提交 `config/coordinates.json`、`data/`、数据库或抓取结果
- Stage 1 会主动控制鼠标和滚轮，务必保留 `pyautogui` failsafe
- 任何影响窗口激活、点击位置、标签管理的改动，都需要在 Windows/macOS 上分别验证
