# 🚂 CRTicketMonitor 国铁余票查询与监控

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)

这是一个轻量查询和监控12306余票的工具，使用Gemini辅助开发。

---

### 核心功能

* **席位覆盖**：支持商务座、一等座、二等座、软座、卧铺等常用席位查询；
* **车站同步**：自动从 12306 官方实时抓取最新的车站代码映射表；
* **异常自动纠错**：查询时若输入了本地未记录的车站，程序会自动触发二次同步，确保查询成功；
* **双模式监控**：
    * **自动模式 (Auto)**：自定义随机间隔刷新，适合长时间挂机监控。
    * **手动模式 (Manual)**：按需手动刷新，灵活掌握查询节奏。
* **高亮视觉提醒**：查询到有票的车次时，车次编号将以 **绿色** 显著标出。

---

### 环境准备

在运行此程序之前，你需要安装以下依赖库：

1.  **Requests**: 用于处理网络请求。
2.  **PrettyTable**: 用于在终端输出表格。

你可以通过 `requirements.txt` 一键安装：
```bash
pip install -r requirements.txt
```

### 快速开始
1. 克隆/下载项目：
将`main.py`下载到你的本地目录。

2. 运行程序：
```bash
python main.py
```

3. 操作指令：
- `R`: 放弃当前监控，返回初始界面重新输入。
- `Q`: 安全退出程序。
- `M`: 从自动刷新切换到手动模式。
- `M`: 从手动模式切换回自动刷新。
- `Enter`: 在任何模式下立即强制刷新一次。

### 目录结构
``````bash
.
├── main.py                # 程序主逻辑代码
├── requirements.txt       # 依赖库清单
├── README.md              # 项目说明文档
└── station_codes.json     # 运行后自动生成的车站缓存数据
``````

### 免责声明

本工具仅用于学习交流编程技术。请勿用于任何商业用途，使用时请遵守 12306 官方平台的频率限制，避免由于请求过快导致 IP 被封禁。
