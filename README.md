# 微信公众号历史文章采集工具

Electron 桌面应用，用于采集微信公众号历史文章链接并抓取正文内容。当前仓库只支持 Electron 桌面产品形态；Python 仍然负责自动化、数据库和导入导出能力，但这些能力通过本地 sidecar 由桌面应用调用，不再作为独立用户入口暴露。

## 产品组成

- `desktop/`: Electron + React + TypeScript 桌面前端
- `desktop_backend/`: Python sidecar，本地提供查询、任务执行和导入导出接口
  - 入口与路由：`desktop_backend/app.py`、`desktop_backend/server.py`、`desktop_backend/server_routes.py`、`desktop_backend/server_runtime.py`、`desktop_backend/import_export_handlers.py`、`desktop_backend/runtime.py`
  - 任务与事件：`desktop_backend/task_registry.py`、`desktop_backend/task_events.py`、`desktop_backend/tasks/workflow_handlers.py`
  - 统计查询：`desktop_backend/statistics.py`
  - 文章域：`desktop_backend/articles/`（含 `query_handlers.py`、`command_handlers.py`、`payloads.py`）
  - 任务实现：`desktop_backend/tasks/calibration/`、`desktop_backend/tasks/collection/`、`desktop_backend/tasks/scraping/`
- `scraper/`: 采集与抓取核心逻辑
- `services/`: 校准、采集、抓取、导入导出等共享流程
- `storage/`: SQLite 与 HTML/Markdown 文件落盘

## 主要能力

- 阶段 1：通过微信 PC 客户端自动采集文章链接
- 阶段 2：通过 Playwright 抓取文章正文、发布时间和账号信息
- 桌面端校准、任务进度、文章管理、失败重试、数据导入导出
- SQLite 持久化与本地 HTML/Markdown 备份

## 环境准备

### Python sidecar 环境

```bash
conda create -n wechat-scraper python=3.10
conda activate wechat-scraper
pip install -r requirements.txt
playwright install chromium
```

### Electron 前端环境

- Node.js 建议使用 20.x 或更新的稳定版本

```bash
npm --prefix desktop install
```

## 开发启动

### 方式一：手动分开启动

适合调试 sidecar 或单独查看后端日志。

```bash
conda activate wechat-scraper
python -m desktop_backend.app
```

另开一个终端启动 Electron 开发环境：

```bash
npm --prefix desktop run dev
```

### 方式二：由 Electron 自动拉起 sidecar

Electron 主进程会按以下顺序寻找 sidecar：

1. `DESKTOP_BACKEND_EXECUTABLE`
2. `DESKTOP_BACKEND_PYTHON`
3. 当前 Conda 环境中的 Python
4. 打包产物资源目录中的 sidecar 可执行文件

如果 sidecar 启动失败，桌面界面会保留并显示错误状态。

## 常用开发与验证命令

```bash
npm --prefix desktop run dev
npm --prefix desktop run build
npm --prefix desktop run build:sidecar
npm --prefix desktop run package:desktop
npm --prefix desktop run typecheck
npm --prefix desktop run test
npm --prefix desktop run e2e
```

Python 侧验证：

```bash
conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_structure -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_queries -v
conda run -n wechat-scraper python -m unittest tests.test_desktop_backend_server -v
```

推荐的最小回归验证组合：

```bash
conda run -n wechat-scraper python -m unittest tests.test_electron_only_repo -v
npm --prefix desktop run typecheck
npm --prefix desktop run test
```

## 打包说明

Electron 桌面壳是唯一支持的分发路径。**完整、可独立分发的安装包必须包含 frozen Python sidecar**（PyInstaller 将 `desktop_backend` 打成 **onedir** 应用目录：可执行文件在 `desktop-backend/` 内），否则最终用户机器上仍需自行准备 Python 与依赖。

Stage 2 抓取依赖 Playwright Chromium。**打包前在构建机上执行 `playwright install chromium`**（与 `pip install -r requirements.txt` 同一 Conda 环境），以便 `scripts/build_desktop_sidecar.py` 能把本机 Playwright 缓存中 **与 Chromium 抓取相关的条目**（`chromium-*`、`chromium_headless_shell-*`、存在的 `ffmpeg-*`）复制到 `build/desktop-sidecar/ms-playwright/`，而不会把 Firefox/WebKit 等一并打入包内。electron-builder 会把它与可执行文件一并放入 **`resources/sidecar/ms-playwright/`**。冻结运行的 sidecar 会通过 `PLAYWRIGHT_BROWSERS_PATH` 指向该目录（由 `configure_runtime_environment()` 设置）；也可用环境变量 `PLAYWRIGHT_BROWSERS_PATH` 覆盖安装源或调试路径。

### 推荐流程（`package:desktop`）

```bash
npm --prefix desktop run build
npm --prefix desktop run package:desktop
```

`package:desktop`（以及 `package:desktop:dir`）会在调用 electron-builder **之前**先构建 frozen Python sidecar：产物落在仓库根目录的 `build/desktop-sidecar/desktop-backend/`（内含 `_internal/` 与入口二进制），Playwright 资源仍在同级的 `build/desktop-sidecar/ms-playwright/`；electron-builder 复制到应用包 **`resources/sidecar/`**。运行时入口为 **`resources/sidecar/desktop-backend/desktop-backend`**（macOS/Linux）或 **`resources/sidecar/desktop-backend/desktop-backend.exe`**（Windows）；详见 [`docs/electron-desktop-ui.md`](docs/electron-desktop-ui.md)。

### 仅构建 sidecar（不打包 Electron）

需要单独刷新 PyInstaller 产物时使用（与 `package:desktop` 中的步骤相同）：

```bash
npm --prefix desktop run build:sidecar
```

等价于在**仓库根目录**、已激活 `wechat-scraper` 环境时执行：

```bash
python scripts/build_desktop_sidecar.py
```

### 原生平台构建（native platform）

- **macOS** 安装包应在 **macOS** 上执行 `package:desktop`（或 `package:desktop:dir`）。
- **Windows** 安装包应在 **Windows** 上执行相同脚本。

交叉编译 frozen sidecar 与 Electron 原生依赖不可靠，发布前请在目标 **native platform** 上完整打一次包并冒烟验证。

### 开发与调试（非最终用户路径）

日常开发仍可直接用 Python 启动 sidecar，便于查看日志与断点：

```bash
conda activate wechat-scraper
python -m desktop_backend.app
```

再配合 `npm --prefix desktop run dev`，或由 Electron 通过 `DESKTOP_BACKEND_PYTHON` / 当前 Conda 环境自动拉起。自定义布局或 CI 覆盖物可使用 `DESKTOP_BACKEND_EXECUTABLE`。

如果你改动了启动或打包逻辑，也应同步更新 [`docs/electron-desktop-ui.md`](docs/electron-desktop-ui.md)。

## 运行时数据

- macOS：`~/Library/Application Support/WeChatScraper/`
- Windows：`%APPDATA%\\WeChatScraper\\`

运行时目录中会包含：

- `config/coordinates.json`
- `data/articles.db`
- `data/articles/html/`
- `data/articles/markdown/`
- 启动日志和 sidecar 相关日志

这些内容属于本机运行时数据，不应提交到仓库。

## 故障排查

- 启动后前端显示后端未连接：先检查 sidecar 是否已启动，以及 `DESKTOP_BACKEND_EXECUTABLE` / `DESKTOP_BACKEND_PYTHON` 是否指向有效目标
- 打包后的应用一闪而退：检查运行时目录中的启动日志
- macOS 未签名应用无法直接打开：可在目标机器上手动移除 quarantine，或使用 Developer ID 签名并完成 notarization
- 采集前请先在桌面应用的校准页面完成坐标校准；Stage 1 会真实移动和点击鼠标
- 如果切到新的 git worktree，记得在该 worktree 内重新执行 `npm --prefix desktop install`，因为 `desktop/node_modules` 不会自动共享

## 仓库结构

```text
wechat_official_account_collect_tool/
├── desktop/                  # Electron + React 桌面前端
├── desktop_backend/          # Python sidecar
├── scraper/                  # 采集与抓取核心逻辑
├── services/                 # 校准、工作流、导入导出
├── storage/                  # 数据库与文件存储
├── tests/                    # Python 测试
├── assets/                   # 图标等静态资源
├── config/                   # 本机运行时配置（gitignored）
├── data/                     # 本机运行时数据（gitignored）
└── README.md
```

## 许可证

MIT License
