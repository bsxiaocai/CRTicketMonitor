# CRTicketMonitor - 12306 余票查询与监控助手

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT) [![Version](https://img.shields.io/badge/version-3.3.0-orange.svg)](https://github.com/)

轻量级 12306 余票查询与实时监控工具，基于 PySide6 图形界面。使用 AI 辅助开发。

---

## 核心功能

### GUI 图形界面

- **可视化查询**：基于 PySide6 的现代化界面，操作直观
- **窗口自适应**：自动适配屏幕大小，居中显示
- **高级筛选面板**：实时筛选，即时刷新结果
  - 车次类型：G/C、D、Z、T、K、其他 / 复兴号 / 智能动车组
  - 出发站 / 到达站：多选，支持拼音搜索和同城车站智能过滤
  - 席别：商务座、一等座、二等座、软卧、硬卧、无座
  - 发车时段：凌晨 / 上午 / 下午 / 晚间
- **表格排序**：点击"开点""到点""历时"列头升降序排列
- **收藏功能**：收藏车次黄底高亮，有票车次绿底高亮
- **监控模式**：自动模式（随机间隔刷新）/ 手动模式
- **多渠道通知**：Windows Toast、企业微信、飞书、钉钉
- **快捷跳转**：一键打开 12306 预填信息页面

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：

| 包名 | 用途 |
|---|---|
| PySide6 >= 6.5.0 | GUI 图形界面 |
| requests >= 2.28.0 | HTTP 网络请求 |
| prettytable >= 3.0.0 | 表格格式化输出 |
| pypinyin >= 0.48.0 | 车站拼音搜索 |
| pyinstaller >= 6.0.0 | 打包工具 |

### 运行程序

```bash
python main.py
```

### 打包为 EXE

```bash
pyinstaller --clean CRTicketMonitor.spec
```

打包完成后，`dist/CRTicketMonitor.exe` 可独立运行，无需 Python 环境。

---

## GUI 操作指南

### 主界面布局

1. **查询条件栏**：出发站、到达站（支持拼音输入 + "选择"按钮）、日期选择、"查询"按钮、"打开 12306"按钮
2. **功能按钮栏**：开始监控、停止监控、收藏选中车次、重置查询与筛选
3. **筛选面板**：车次类型、车站、席别、时段筛选（勾选即生效）
4. **结果表格**：车次信息和余票数据

### 查询操作

1. 输入出发站、到达站名称（支持拼音首字母），或点击"选择"按钮弹出车站选择器
2. 选择出发日期
3. 点击"查询"获取余票信息

### 筛选功能

所有筛选条件**实时生效**，勾选后表格立即刷新。

- **车次类型**：勾选 G/C、D、Z、T、K、其他，或筛选复兴号 / 智能动车组
- **车站筛选**：多选出发站 / 到达站，输入城市名可过滤同城车站
- **席别筛选**：勾选后仅显示有对应席别的车次
- **时段筛选**：下拉选择凌晨 / 上午 / 下午 / 晚间

### 表格操作

- 点击"开点""到点""历时"列头排序
- 右键菜单：收藏 / 取消收藏
- 双击车次：切换收藏状态

### 监控与通知

1. 点击"开始监控"，选择自动或手动模式
2. 自动模式按随机间隔刷新，发现有票车次时发送通知
3. 通知渠道在 `config.json` 中配置

---

## 项目结构

```
CRTicketMonitor/
├── main.py                         # 主程序入口
├── CRTicketMonitor.spec            # PyInstaller 打包配置
├── config.json                     # 程序配置文件
├── station_codes.json              # 车站代码缓存
├── railway.ico                     # 程序图标
├── build_exe.bat                   # Windows 打包脚本
├── requirements.txt                # Python 依赖
│
├── core/                           # 核心功能模块
│   ├── ticket_api.py               # 12306 API 请求
│   ├── ticket_parser.py            # 票务信息解析
│   ├── train_classifier.py         # 车次分类（含复兴号 / 智能动车组识别）
│   └── time_filter.py              # 时间筛选器
│
├── ui/                             # 用户界面模块
│   └── gui/
│       ├── main_window.py          # PySide6 主窗口
│       └── filter_panel.py         # 筛选面板组件
│
├── services/                       # 业务服务模块
│   ├── query_service.py            # 查询服务
│   ├── favorite_service.py         # 收藏服务
│   ├── cache_service.py            # 缓存服务
│   ├── station_search_service.py   # 车站搜索服务
│   ├── export_service.py           # 导出服务
│   └── monitor_manager.py          # 监控任务管理
│
├── config/                         # 配置管理模块
│   └── config_manager.py           # 配置管理器
│
├── logger/                         # 日志模块
│   ├── ticket_logger.py            # 日志记录器
│   └── query_history.py            # 查询历史记录
│
├── notification/                   # 通知模块
│   ├── base.py                     # 通知基类
│   ├── channels.py                 # 通知渠道（Windows / 企微 / 飞书 / 钉钉）
│   └── manager.py                  # 通知管理器
│
└── dist/                           # 打包输出目录
    ├── CRTicketMonitor.exe         # 可执行文件
    ├── config.json                 # 运行时配置
    ├── station_codes.json          # 运行时车站数据
    └── logs/                       # 日志目录
```

---

## 配置说明

配置文件为 `config.json`，主要选项：

| 配置项 | 说明 | 默认值 |
|---|---|---|
| `dc_classification.default_mode` | D/C 识别模式：`official`（全归动车）/ `smart`（低号段归普通车） | official |
| `notification.enabled` | 是否启用通知 | true |
| `notification.cooldown_seconds` | 通知冷却时间（秒） | 300 |
| `notification.only_target_trains` | 仅监控目标车次 | false |
| `notification.min_tickets` | 触发通知的最小余票数 | 1 |
| `notification.channels` | 通知渠道配置（Windows Toast / 企微 / 飞书 / 钉钉） | - |
| `gui.default_monitor_interval` | 默认监控间隔（秒） | 30 |

---

## 免责声明

本工具仅用于学习交流编程技术。请勿用于商业用途，使用时请遵守 12306 官方平台的频率限制，避免请求过快导致 IP 被封禁。

---

## 许可证

本项目采用 [MIT](LICENSE) 许可证。Copyright (c) 2026 BH7GUL.
