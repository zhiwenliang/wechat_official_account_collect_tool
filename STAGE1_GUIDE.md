# 阶段1使用指南

## 环境准备

### 1. 创建conda环境
```bash
# 使用environment.yml创建环境
conda env create -f environment.yml

# 激活环境
conda activate wechat-scraper
```

### 2. 安装Playwright浏览器（阶段2需要）
```bash
playwright install chromium
```

### 3. 测试基础功能
```bash
python test_stage1.py
```
选择选项测试：
- 选项1: 测试鼠标位置获取
- 选项2: 测试剪贴板读写
- 选项3: 测试点击功能

## 使用流程

### 1. 准备微信窗口
1. 打开微信PC客户端
2. 窗口1：打开目标公众号页面
3. 窗口2：随便点击一篇文章，打开微信内置浏览器
4. 调整两个窗口位置，确保不重叠且都可见

### 2. 校准坐标
```bash
python main.py calibrate
```
按提示依次记录4个位置：
- 文章分组按钮
- 文章列表点击区域
- 右上角更多按钮
- 复制链接菜单项

### 3. 开始采集
```bash
python main.py collect
```

## 配置调整

编辑 `config/coordinates.json`：
- `timing.page_load_wait`: 页面加载等待（默认2秒）
- `timing.menu_open_wait`: 菜单展开等待（默认0.5秒）
- `collection.max_articles`: 最大采集数量（默认1000）
- `collection.duplicate_threshold`: 连续重复阈值（默认5）

## 注意事项

1. **紧急停止**: 鼠标移到屏幕左上角可停止
2. **窗口固定**: 校准后不要移动窗口
3. **不要干扰**: 采集时不要操作电脑
4. **网络延迟**: 网络慢时增加等待时间

## 输出

链接保存在: `data/links.txt`
