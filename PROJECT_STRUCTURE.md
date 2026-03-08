# CRTicketMonitor 项目结构说明

## 项目概述

12306余票监控工具 - 用于查询和监控铁路余票信息

**版本**: 2.1.0
**设计者**: BH7GUL

---

## 目录结构

```
CRTicketMonitor/
├── main.py                    # 主程序入口
├── CRTicketMonitor.spec       # PyInstaller打包配置文件
├── config.json               # 程序配置文件
├── station_codes.json        # 车站代码缓存文件
├── railway.ico               # 程序图标
├── requirements.txt          # Python依赖列表
├── setup.py                  # 安装配置
│
├── core/                     # 核心功能模块
│   ├── __init__.py
│   ├── ticket_api.py         # 12306 API请求模块
│   ├── ticket_parser.py      # 票务信息解析模块
│   ├── train_classifier.py   # 车次分类器
│   └── time_filter.py        # 时间筛选器
│
├── ui/                       # 用户界面模块
│   ├── __init__.py
│   ├── cli_menu.py           # 命令行菜单
│   ├── display.py            # 显示模块
│   └── filter_menu.py        # 筛选菜单
│
├── services/                 # 业务服务模块
│   ├── __init__.py
│   ├── query_service.py      # 查询服务
│   └── export_service.py     # 导出服务
│
├── config/                   # 配置管理模块
│   ├── __init__.py
│   └── config_manager.py     # 配置管理器
│
├── logger/                   # 日志模块
│   ├── __init__.py
│   ├── ticket_logger.py      # 日志记录器
│   └── query_history.py      # 查询历史记录
│
├── notification/             # 通知模块
│   ├── __init__.py
│   ├── base.py               # 通知基类
│   ├── channels.py           # 通知渠道实现
│   └── manager.py            # 通知管理器
│
├── test/                     # 测试模块
│   ├── __init__.py
│   └── test_all.py           # 测试文件
│
├── past_version/             # 历史版本
│   ├── README.txt
│   └── main_v1.0.1.py        # v1.0.1版本源码
│
├── build/                    # 打包中间文件（自动生成）
│   └── CRTicketMonitor/      # PyInstaller构建目录
│
└── dist/                     # 打包输出目录
    ├── CRTicketMonitor.exe   # 打包后的可执行文件
    └── config.json           # 配置文件副本
```

---

## 文件说明

### 根目录文件

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序入口，负责初始化各模块并启动CLI菜单 |
| `CRTicketMonitor.spec` | PyInstaller打包配置，定义打包参数和包含的文件 |
| `config.json` | 用户配置文件，包含通知设置、日志设置等 |
| `station_codes.json` | 车站名称与代码的映射缓存，首次运行自动下载 |
| `railway.ico` | 程序图标文件 |
| `requirements.txt` | Python依赖包列表 |

### 核心模块 (core/)

| 文件 | 说明 |
|------|------|
| `ticket_api.py` | 负责与12306 API交互，获取车站编码和余票信息 |
| `ticket_parser.py` | 解析API返回的票务数据，转换为结构化格式 |
| `train_classifier.py` | 车次分类逻辑（高铁/动车/普快等） |
| `time_filter.py` | 按时间段筛选车次 |

### 界面模块 (ui/)

| 文件 | 说明 |
|------|------|
| `cli_menu.py` | 命令行主菜单，处理用户交互 |
| `display.py` | 格式化显示查询结果 |
| `filter_menu.py` | 筛选和排序功能菜单 |

### 服务模块 (services/)

| 文件 | 说明 |
|------|------|
| `query_service.py` | 查询业务逻辑，整合API调用和数据解析 |
| `export_service.py` | 导出查询结果到JSON文件 |

### 配置模块 (config/)

| 文件 | 说明 |
|------|------|
| `config_manager.py` | 配置文件读写管理，支持深度合并配置 |

### 日志模块 (logger/)

| 文件 | 说明 |
|------|------|
| `ticket_logger.py` | 日志记录，支持文件和控制台输出 |
| `query_history.py` | 查询历史记录，存储在SQLite数据库中 |

### 通知模块 (notification/)

| 文件 | 说明 |
|------|------|
| `base.py` | 通知渠道基类定义 |
| `channels.py` | 具体通知渠道实现（Windows通知、企业微信、飞书、钉钉） |
| `manager.py` | 通知管理器，协调各通知渠道 |

---

## 打包说明

### 打包命令

```bash
pyinstaller --clean CRTicketMonitor.spec
```

### 打包后文件分布

打包完成后，`dist/` 目录包含：

- `CRTicketMonitor.exe` - 可执行文件
- `config.json` - 配置文件（需手动复制）

### 首次运行

1. 确保 `config.json` 和 `CRTicketMonitor.exe` 在同一目录
2. 双击运行 `CRTicketMonitor.exe`
3. `station_codes.json` 会自动下载到exe同目录
4. `logs/` 目录会自动创建用于存储日志

---

## 配置文件说明 (config.json)

```json
{
    "dc_classification": {
        "default_mode": "official",    // DC识别模式: official/smart
        "smart_threshold": 899         // 智能模式阈值
    },
    "notification": {
        "enabled": true,               // 是否启用通知
        "cooldown_seconds": 300,       // 通知冷却时间
        "only_target_trains": false,   // 仅通知目标车次
        "min_tickets": 1               // 最小余票数
    },
    "logging": {
        "level": "INFO",               // 日志级别
        "max_size_mb": 10,             // 单个日志文件最大大小
        "backup_count": 5              // 保留日志文件数
    }
}
```

---

## 运行日志

程序运行日志存储在 `logs/` 目录下：
- `tickets.log` - 主日志文件
- `query_history.db` - 查询历史SQLite数据库

---

## 常见问题

### exe闪退问题

如果exe运行后立即闪退，请检查：
1. `config.json` 是否与exe在同一目录
2. 是否有网络连接（首次运行需要下载车站数据）
3. 查看 `logs/` 目录下的日志文件获取错误信息

### 车站数据更新

`station_codes.json` 会在每次启动时自动从12306服务器更新。如果网络不可用，将使用本地缓存。

---

*文档更新日期: 2026-03-08*