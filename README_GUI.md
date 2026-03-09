# 12306 余票监控工具 v2.2.0 - GUI 版本

## 新增功能

### 一、GUI 界面（PySide6）

**启动方式：**
```bash
# Windows
run_gui.bat

# 或命令行
python main.py --gui
```

**界面功能：**
- 输入区域：出发站、到达站、日期选择、车次筛选、座位筛选
- 按钮区域：查询、开始监控、停止监控、收藏选中车次
- 结果区域：表格显示所有车次信息

### 二、车次收藏夹

**功能说明：**
- 收藏的车次在查询结果中优先显示
- 收藏车次用黄色高亮标记
- 双击车次可快速收藏/取消收藏

**使用方法：**
1. 在 GUI 中选中车次，点击"收藏选中车次"按钮
2. 或直接双击车次行
3. 菜单"编辑" -> "管理收藏"可查看和管理收藏列表

**数据文件：** `favorites.json`

### 三、监控成功自动打开 12306

**配置方法：**
1. GUI 菜单："设置" -> "自动打开 12306"（勾选启用）
2. 或编辑 `config.json`：
```json
{
    "auto_open_12306": true
}
```

**功能说明：**
- 监控发现有票时自动打开浏览器跳转到 12306 官网
- 配合系统通知使用效果更佳

### 四、查询缓存机制

**功能说明：**
- 相同查询条件（出发站、到达站、日期）10 秒内重复查询
- 直接返回缓存结果，减少 12306 服务器压力
- 缓存自动过期，无需手动管理

**技术实现：**
- `services/cache_service.py`
- TTL=10 秒，自动清理过期缓存

### 五、车站输入自动补全

**功能说明：**
- 输入站名时自动显示候选列表
- 支持拼音首字母搜索：
  - `bj` -> 北京、北京北、北京南...
  - `sh` -> 上海、上海虹桥...
  - `cs` -> 长沙
  - `wh` -> 武汉

**支持的车站：**
- 北京、上海、广州、深圳、长沙、武汉、成都、重庆、天津、南京、杭州、西安等

### 六、查询结果高亮

**高亮规则：**
| 条件 | 颜色 |
|------|------|
| 有票 | 绿色 |
| 收藏车次 | 黄色 |
| 无票（非收藏） | 灰色 |

### 七、监控任务管理

**功能说明：**
- 支持同时监控多个任务
- 每个任务独立运行，可设置不同的查询间隔
- GUI 界面显示所有任务状态

**示例：**
- 任务 1：长沙 → 武汉，间隔 30 秒
- 任务 2：长沙 → 深圳，间隔 60 秒

## 目录结构

```
CRTicketMonitor/
├── main.py                     # 主程序入口
├── config.json                 # 配置文件
├── station_codes.json          # 车站数据
├── favorites.json              # 收藏数据（运行时创建）
├── requirements.txt            # Python 依赖
├── run_gui.bat                 # GUI 启动脚本（Windows）
├── run_cli.bat                 # CLI 启动脚本（Windows）
├── core/                       # 核心业务层
│   ├── ticket_api.py          # 12306 API 客户端
│   ├── ticket_parser.py       # 车票数据解析
│   ├── train_classifier.py    # 车次分类
│   └── time_filter.py         # 时间筛选
├── services/                   # 服务层
│   ├── query_service.py       # 查询服务（含缓存支持）
│   ├── export_service.py      # 导出服务
│   ├── favorite_service.py    # 收藏服务（新增）
│   ├── cache_service.py       # 缓存服务（新增）
│   ├── station_search_service.py  # 车站搜索（新增）
│   └── monitor_manager.py     # 监控任务管理（新增）
├── notification/               # 通知系统
│   ├── manager.py             # 通知管理器（支持自动打开 12306）
│   ├── base.py                # 基础类定义
│   └── channels.py            # 通知渠道实现
├── ui/                         # 用户界面
│   ├── cli_menu.py            # CLI 菜单
│   └── gui/                   # GUI 界面（新增）
│       ├── __init__.py
│       └── main_window.py     # 主窗口
└── logger/                     # 日志系统
```

## 安装说明

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖说明：**
- `PySide6>=6.5.0` - GUI 框架（仅 GUI 模式需要）
- `requests>=2.28.0` - HTTP 请求
- `prettytable>=3.0.0` - 表格格式化
- `pypinyin>=0.48.0` - 拼音支持（可选，用于车站搜索）

### 2. 启动程序

**GUI 模式：**
```bash
python main.py --gui
```

**CLI 模式（兼容原版本）：**
```bash
python main.py
```

## 配置文件说明

### config.json

```json
{
    "auto_open_12306": false,        // 是否自动打开 12306 网页
    "gui": {
        "default_monitor_interval": 30,  // 默认监控间隔（秒）
        "theme": "light"                 // GUI 主题
    },
    "notification": {
        "enabled": true,
        "cooldown_seconds": 300,
        "only_target_trains": false,
        "min_tickets": 1
    }
}
```

## 使用示例

### GUI 模式

1. 启动程序：`python main.py --gui`
2. 输入出发站和到达站（支持拼音首字母）
3. 选择日期（默认今天，可选 15 天内）
4. 点击"查询"按钮查看余票
5. 点击"开始监控"自动定时查询
6. 双击车次可收藏/取消收藏
7. 监控到有票时会自动通知并打开 12306（如果启用）

### CLI 模式

保持原有使用方式不变：
```bash
python main.py
```

## 版本历史

- **v2.2.0** - GUI 版本
  - 新增 PySide6 GUI 界面
  - 新增车次收藏夹功能
  - 新增查询缓存机制
  - 新增车站输入自动补全
  - 新增查询结果高亮显示
  - 新增多任务监控管理
  - 新增监控成功自动打开 12306

- **v2.1.0** - CLI 版本
  - 基础查询功能
  - 监控功能
  - 通知系统
  - 历史记录

## 注意事项

1. GUI 模式需要安装 PySide6，约 150MB
2. 车站自动补全目前仅支持常见城市
3. 缓存时间为 10 秒，频繁查询时注意缓存生效
4. 自动打开 12306 功能需要默认浏览器已正确配置
5. 收藏夹数据保存在 `favorites.json`，可手动编辑

## 技术支持

如有问题，请检查：
1. Python 版本（建议 3.8+）
2. 依赖是否完整安装
3. 网络连接是否正常
4. 车站名称是否正确
