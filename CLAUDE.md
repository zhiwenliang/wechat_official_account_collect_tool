# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

微信公众号历史文章采集工具，分两个阶段：
1. 通过pyautogui控制微信PC客户端采集文章链接
2. 通过Playwright访问链接抓取文章详细内容

## 核心命令

```bash
# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium

# 完整工作流程
python main.py calibrate  # 1. 校准坐标（首次使用必须）
python main.py test       # 2. 测试校准结果（可选）
python main.py collect    # 3. 采集链接（需要手动准备微信窗口）
python main.py import     # 4. 导入链接到数据库
python main.py scrape     # 5. 抓取文章内容

# 查看数据库状态
sqlite3 data/articles.db "SELECT status, COUNT(*) FROM articles GROUP BY status;"
```

## 架构设计

### 阶段1：链接采集（scraper/link_collector.py）
- 使用pyautogui通过固定坐标点击微信窗口
- 用户需手动左右分屏：左侧公众号窗口 + 右侧微信内置浏览器
- 操作流程：点击文章 → 点击"更多" → 点击"复制链接" → 从剪贴板读取
- 链接保存到 data/links.txt

### 阶段2：内容抓取（scraper/content_scraper.py）
- 使用Playwright访问文章URL
- 提取：标题、发布时间、阅读量、点赞数、正文HTML
- 保存到SQLite数据库 + HTML文件

### 数据存储
- SQLite: storage/database.py - 结构化数据
- 文件系统: storage/file_store.py - HTML备份，按月份组织

## 关键技术点

1. **坐标配置**: config/coordinates.json 存储所有按钮坐标，通过calibrator.py校准
2. **去重机制**: 连续5个重复链接则停止采集
3. **状态管理**: pending → scraped/failed
4. **等待策略**: 页面加载2秒，菜单展开0.5秒（可配置）

## 注意事项

- 坐标校准后窗口位置不能变动
- 采集过程中不要移动鼠标或操作电脑（鼠标移到屏幕角落可紧急停止）
- 微信文章图片有防盗链，需要带referer下载
- 阅读量是动态加载的，可能获取失败
- 到底检测：连续5次相同链接时，先向上再向下滚动刷新页面，如果刷新后仍然5次相同则确认到底
- 每30篇文章自动清理浏览器标签，防止内存占用过高
- 滚动后等待2秒，确保页面加载完成
- Windows和macOS窗口激活机制不同，程序会自动适配

## 数据库结构

articles表字段：
- id: 自增主键
- title: 文章标题
- url: 文章链接（唯一索引）
- publish_time: 发布时间
- read_count: 阅读量
- like_count: 点赞数
- scraped_at: 抓取时间
- status: pending（待抓取）| scraped（已抓取）| failed（失败）
- file_path: HTML文件路径
