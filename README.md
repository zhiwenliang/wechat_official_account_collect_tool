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
  - 失败自动重试（默认3次，间隔10秒）

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

# 3. 采集链接（需要手动准备微信窗口，链接直接存入数据库）
python main.py collect

# 4. 抓取文章内容（完成后自动生成索引）
python main.py scrape

# 5. 查看数据库统计信息
python main.py stats

# 6. 重新抓取失败的文章
python main.py retry

# 7. 单独生成文章目录索引（可选）
python main.py index

# 8. 导出数据库和文章备份为一个 zip 数据包
python main.py export-data backup.zip

# 9. 导入外部数据库文件（只替换数据库）
python main.py import-db C:\\path\\to\\articles.db
```

## 打包可执行程序

项目提供了统一打包脚本，并带有 GitHub Actions 工作流用于生成 GUI 可执行程序。
当前推荐通过 Actions 生成以下内部使用产物：
- `wechat-scraper-gui-macos-arm64.zip`
- `wechat-scraper-gui-windows-x64.zip`

打包完成后，脚本会自动把 Playwright 的 Chromium 浏览器目录复制到产物运行目录旁边，解压后即可直接执行阶段 2 抓取。

### 推荐：通过 GitHub Actions 打包 GUI

仓库内置工作流：`.github/workflows/package-gui.yml`

使用方式：
1. 打开 GitHub 仓库的 **Actions** 页面
2. 选择 **Package GUI Executables**
3. 点击 **Run workflow**
4. 等待 `macos-14` 和 `windows-latest` 两个任务完成
5. 在该次 workflow 的 Artifacts 中下载打包结果

说明：
- macOS 产物仅面向 Apple Silicon（arm64）
- Windows 产物面向 x64
- 当前产物未签名、未 notarize，仅适合内部使用
- CI 会校验 `.app` / `.exe` 和 `ms-playwright` 浏览器目录是否存在，不完整产物会直接失败

### 本地手动打包

```bash
# 如需重新生成默认图标资源
python scripts/generate_icon_assets.py

# 安装项目依赖和打包依赖
pip install -r requirements.txt pyinstaller

# 安装 Playwright Chromium
playwright install chromium

# 生成 GUI 分发压缩包
python scripts/package_app.py --target gui --archive

# macOS 共享给其他人时，可选：使用证书签名 .app
python scripts/package_app.py --target gui --archive \
  --macos-codesign-identity "Developer ID Application: Your Name (TEAMID)"
```

生成结果默认输出到 `dist/<platform>/`，例如：
- `dist/macos-arm64/wechat-scraper-gui-macos-arm64.zip`
- `dist/windows-x64/wechat-scraper-gui-windows-x64.zip`

如需本地生成未压缩产物或其他目标，也可以继续使用：

```bash
# 同时打包 GUI 和 CLI
python scripts/package_app.py

# 只打包 GUI
python scripts/package_app.py --target gui

# 只打包 CLI
python scripts/package_app.py --target cli

# 打包成单文件
python scripts/package_app.py --target gui --onefile
```

注意：
- 需要在目标平台上执行打包，不能跨平台直接生成可执行文件
- 打包环境应当先确认 `python -m gui.main` 可以正常启动，再执行 PyInstaller
- 打包前需要先在构建机执行 `playwright install chromium`
- 打包后的程序会优先使用产物旁边的 `ms-playwright` 浏览器目录
- 若未显式传入 `--icon`，打包脚本会默认使用 `assets/icons/wechat-scraper.icns` 或 `assets/icons/wechat-scraper.ico`
- 若传入 `--macos-codesign-identity`，打包脚本会在复制 Playwright 浏览器后对 `.app` 执行 `codesign`
- 本地 macOS 打包若用于当前仓库约定的分发目标，应在 Apple Silicon 机器上执行

### 内部使用注意事项

- macOS 未签名应用首次打开时，可能需要在 Finder 中右键应用后选择“打开”，或在“系统设置 -> 隐私与安全性”中允许执行
- Windows 未签名程序可能触发 SmartScreen，通常需要点击“更多信息”后再选择“仍要运行”
- 打包后的运行时数据不会写入 `.app` 或 `.exe` 目录
- macOS 运行时数据目录：`~/Library/Application Support/WeChatScraper/`
- Windows 运行时数据目录：`%APPDATA%\\WeChatScraper\\`
- 坐标配置会保存到上述目录下的 `config/coordinates.json`
- 数据库和导出的文章会保存到上述目录下的 `data/`
- 如果 GUI 应用启动时只在 Dock 或任务栏闪一下就退出，请检查上述运行时目录中的 `wechat-scraper-startup.log`
- 如果 macOS 提示“已损坏，无法打开”，通常是 Gatekeeper 拦截了未签名或未 notarize 的应用。临时处理可在接收方机器执行：`xattr -dr com.apple.quarantine /path/to/wechat-scraper-gui.app`
- 如果希望别人下载后直接打开，仍然需要使用 Developer ID 签名并完成 Apple notarization；仅 ad-hoc 签名通常不足以绕过 Gatekeeper

### 查看数据库状态

```bash
sqlite3 data/articles.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"
```

或使用内置命令：
```bash
python main.py stats
```

### 数据库管理

**查看统计信息**：
```bash
python main.py stats
```
显示总文章数、待抓取、已抓取、失败数量，以及失败的文章链接

**重新抓取失败的文章**：
```bash
python main.py retry
```
将所有失败的文章状态重置为待抓取，然后运行 `python main.py scrape` 重新抓取

**导出当前数据包**：
```bash
python main.py export-data backup.zip
```
将当前 `data/articles.db` 以及 `data/articles/html/`、`data/articles/markdown/` 打包成一个 zip 文件，便于备份或迁移。

**导入数据库文件**：
```bash
python main.py import-db C:\path\to\articles.db
```
只替换当前运行时数据库文件，并自动备份旧数据库。注意：该操作不会同步本地 HTML/Markdown 备份目录，因此导入后的数据库记录与本地备份文件可能不一致。

**断点续传**：
如果抓取过程中断，直接再次运行 `python main.py scrape` 即可继续，已抓取的文章会自动跳过

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
- 链接直接保存到数据库

### 阶段2：抓取文章内容

**抓取内容**：
```bash
python main.py scrape
```
- 自动访问所有待抓取的链接
- 提取标题、发布时间、正文HTML
- 自动滚动加载所有图片
- 同时保存HTML和Markdown格式
- 文件名使用发布时间作为前缀：`YYYYMMDD_HHMMSS_标题.md`
- 完成后自动生成文章目录索引：`data/articles/markdown/INDEX.md`

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
│   └── articles/             # 文章备份目录
│       ├── html/             # HTML格式文件
│       │   └── *.html
│       └── markdown/         # Markdown格式文件
│           ├── INDEX.md      # 文章目录索引
│           └── *.md
├── scripts/
│   ├── package_app.py        # 打包脚本
│   └── manual/
│       ├── stage1_check.py   # 阶段1手动检查脚本
│       └── stage2_check.py   # 阶段2手动检查脚本
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

### 数据库的作用

1. **状态管理**：跟踪每个链接的抓取状态（pending/scraped/failed）
2. **断点续传**：抓取中断后可以继续，不会重复抓取已完成的文章
3. **去重**：URL唯一约束，避免重复抓取
4. **失败重试**：记录失败的文章，可以批量重试
5. **统计查询**：快速查看抓取进度和失败情况

## 常见问题

**Q: 校准后采集失败？**
A: 确保窗口位置没有变动，可以运行 `python main.py test` 测试校准结果

**Q: 如何修改最大采集数量？**
A: 编辑 `config/coordinates.json` 中的 `collection.max_articles` 字段

**Q: 图片链接无法访问？**
A: 微信文章图片有防盗链，需要带referer下载

## 许可证

MIT License
