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

# 1. 校准坐标（首次使用必须）
python main.py calibrate

# 2. 采集链接（需要手动准备微信窗口）
python main.py collect

# 3. 导入链接到数据库
python main.py import

# 4. 抓取文章内容
python main.py scrape
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
- 采集过程中不要移动鼠标或操作电脑
- 微信文章图片有防盗链，需要带referer下载
- 阅读量是动态加载的，可能获取失败
