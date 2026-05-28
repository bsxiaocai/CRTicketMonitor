# 更新日志

## v3.4.0 (2026-05-28)

### 稳定性与体验修复

- 中转换乘查询改为后台线程执行，避免切换标签页时阻塞 GUI。
- 导出功能统一使用 `ExportService`，补齐 CSV 导出分支并保留当前表格筛选/排序结果。
- 通知设置保存后即时应用到运行中的查询服务，无需重启程序。
- 默认配置补齐通知渠道和 API 调试开关，并修复默认配置浅拷贝导致的嵌套状态污染风险。
- 新增 `pytest` 基础测试，覆盖车次分类、配置合并、缓存、导出、票务解析、历史记录和中转 worker。

### 架构优化

- 从 `main_window.py`（1945 行）中拆分出 `PriceDetailDialog`、`QueryResultWidget`、6 个 Worker/Signal 类为独立模块，`main_window.py` 缩减至 1363 行
- 新增 `utils/` 共享工具模块：`time_utils.py`（`time_to_minutes` / `duration_to_minutes` / `is_cross_day`）和 `constants.py`（`SEAT_NAMES` / `SEAT_SENTINEL`）
- 消除项目中 5 处时间解析重复代码、5 处哨兵值重复代码、3 处席位常量重复代码
- 移除 `ticket_parser.py` 中的 ANSI 转义码（CLI 模式残留），GUI 不再需要 strip 处理
- `FilterPanel` 改为委托 `StationSearchService` 执行拼音搜索，删除重复的 `_get_pinyin_initials` 方法

### 查询速度优化

- 通知发送改为异步后台线程（fire-and-forget），查询结果不再被通知 I/O 阻塞
- init 页面请求添加缓存标志位，首次查询后跳过后续重复请求，减少一半网络延迟
- 移除 `classify_wrapper` 闭包中每趟车都执行的 `config_manager.get_config()` 冗余调用
- `ticket_parser.py` 循环内的 `TimeFilter` 和 `TicketInfo` import 提升到文件顶层
- `PrettyTable` 创建改为条件化，GUI 模式（`return_table=False`）不再创建无用对象
- `TicketInfo` 新增 `train_type`、`is_fuxing`、`is_smart` 字段，解析时一次计算
- `_convert_tickets_to_data` 直接读取预计算分类字段，UI 线程不再重复调用 `TrainClassifier`
- `QueryResultWidget._refresh_table` 改用 `setRowCount` 预分配 + 背景色内联，减少 widget 操作

### 测试

- 新增 `tests/test_utils.py`：覆盖 `time_to_minutes`、`duration_to_minutes`（含中文格式）、`is_cross_day`、`SEAT_SENTINEL`
- 更新 `tests/test_transfer_worker.py` 导入路径适配模块拆分

### 已知问题

- Windows Toast 通知脚本中 `$notifier` 变量未赋值（`channels.py:37-41`），原生通知可能无法正常工作，`try/except` 吞掉所有异常并返回 True
- `NotificationManager` 的冷却字典和监控集合可能被多个 Worker 线程并发写入，无同步机制
- 转车解析中第二程数据使用硬编码偏移量（33-37），注释标注"needs actual verification"
- `prettytable` 依赖在纯 GUI 模式下仍被保留，未移除


## v3.3.0 (2026-05-25)

### 性能优化

#### 查询异步化
- 将 `_do_query` 中的 HTTP 请求 + 数据解析移到 `QThreadPool` 后台线程执行
- 新增 `QueryWorker(QRunnable)` + `QueryResultSignal(QObject)` 异步查询模式
- 点击查询后 UI 立即显示"正在查询..."状态，界面不再冻结
- 新增 `_is_querying` 防重复查询机制，监控模式下定时器触发不会产生竞态

#### 表格渲染批量优化
- `_refresh_table` 使用 `setSortingEnabled(False)` + `blockSignals(True)` + `setUpdatesEnabled(False)` 包裹批量操作
- `favorites` 查找从 O(n) list comprehension 改为 O(1) `set` 查找（`favorites_set`）
- 消除 `set_data` 后 `_on_filter_changed` 导致的双重表格构建，改用 `_update_filter_label` 仅更新标签

#### 跳过 PrettyTable 生成
- GUI 调用 `execute_query` 时传 `return_table=False`，跳过 PrettyTable 的 `add_row` 和字符串生成
- 减少 CPU 开销，加速数据解析阶段

---

### 架构优化

#### 票价查询改为按需加载
- 删除了批量票价查询机制，改为双击车次行时异步加载单个车次票价
- 使用 `QThreadPool` + `QRunnable` 实现后台线程查询，不阻塞 UI
- 票价弹窗先显示"加载中..."占位，查询完成后自动更新内容
- 删除了 `quick_mode` 参数，查询流程统一简化

#### 监控定时器竞态修复
- 重写了 `MonitorTaskRunner` 的 threading 降级方案
- 使用 `threading.Event.wait(timeout)` 替代 `time.sleep`，`stop()` 可即时唤醒线程
- 共享状态（间隔时间、回调列表）全部加 `threading.Lock` 保护
- 解决了回调列表迭代时修改导致的 `RuntimeError` 风险

#### 缓存策略优化
- 监控模式下绕过缓存直接查询 12306 API，确保数据实时性
- 普通查询保留 10 秒 TTL 缓存，避免短时间内重复请求

#### 解析器索引常量化
- 将 `ticket_parser.py` 中 18 个硬编码的 pipe-delimited 索引抽取为 `FIELD` 常量字典
- 所有索引访问改为常量引用（47 处），12306 调整字段顺序时只需修改一处
- `sort_tickets` 方法的直接索引访问改为 `_safe_get` 安全访问
- 新增 `MIN_FIELDS = 36` 字段数量校验，跳过格式异常的记录

### 代码清理

#### 删除 CLI 界面
- 移除 `ui/cli_menu.py` 和 `ui/filter_menu.py`
- 简化 `main.py` 启动逻辑，直接进入 GUI 模式
- 更新 `CRTicketMonitor.spec` 和 `README.md`

#### 修复代码质量问题
- `main.py` 的 `cleanup()` 函数裸 `except:` 改为 `except Exception:`
- `core/ticket_api.py` 添加 `__del__` 方法兜底关闭文件句柄
- `ui/gui/filter_panel.py` 的 `QLineEdit` 导入从文件底部 hack 移至顶部统一导入
- 删除 `WindowsDesktopNotification` 死代码类（依赖未安装的 win10toast）
- 移除未使用的 `Pillow` 依赖
- 删除 `has_console` 死函数

#### 版本号统一
- 全部版本号统一更新至 3.3.0（main.py / config.json / main_window.py / ticket_logger.py / README.md / build_exe.bat）

---

## v3.2.0

- GUI 图形界面基于 PySide6 实现
- 支持余票查询、自动监控、车次收藏、查询缓存
- 多渠道通知：Windows Toast、企业微信、飞书、钉钉
- 车站拼音搜索、高级筛选面板、结果高亮显示
- CLI 命令行模式（已在此版本移除）
