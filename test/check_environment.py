"""
12306 余票监控工具 - 环境检测脚本
检测所有依赖、模块和功能是否正常
"""

import sys
import os
import importlib

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{'=' * 60}")
    print(f"{text:^60}")
    print(f"{'=' * 60}\n")

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERR] {text}")

def print_warning(text):
    print(f"[WARN] {text}")

def print_info(text):
    print(f"[INFO] {text}")

# 检测结果
results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0
}

def check_module(module_name, display_name=None):
    """检查模块是否可以导入"""
    if display_name is None:
        display_name = module_name

    try:
        importlib.import_module(module_name)
        print_success(f"{display_name}: 已安装")
        results['passed'] += 1
        return True
    except ImportError as e:
        print_error(f"{display_name}: 未安装 ({e})")
        results['failed'] += 1
        return False

def check_file(file_path, description=None):
    """检查文件是否存在"""
    if description is None:
        description = file_path

    if os.path.exists(file_path):
        print_success(f"{description}: 存在")
        results['passed'] += 1
        return True
    else:
        print_error(f"{description}: 不存在 ({file_path})")
        results['failed'] += 1
        return False

def check_function(module, func_name, description=None):
    """检查函数是否存在"""
    if description is None:
        description = func_name

    if hasattr(module, func_name):
        print_success(f"{description}: 可用")
        results['passed'] += 1
        return True
    else:
        print_error(f"{description}: 不可用")
        results['failed'] += 1
        return False

def check_class(module, class_name, description=None):
    """检查类是否存在"""
    if description is None:
        description = class_name

    if hasattr(module, class_name):
        print_success(f"{description}: 可用")
        results['passed'] += 1
        return True
    else:
        print_error(f"{description}: 不可用")
        results['failed'] += 1
        return False

# ============================================
# 开始检测
# ============================================

print_header("12306 余票监控工具 v2.2.0 - 环境检测")

# 1. Python 版本检测
print_header("1. Python 环境检测")
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
if sys.version_info >= (3, 7):
    print_success(f"Python 版本：{python_version}")
    results['passed'] += 1
else:
    print_error(f"Python 版本：{python_version} (需要 3.7+)")
    results['failed'] += 1

# 检查是否有控制台
if sys.stdin.fileno() is not None:
    print_info("运行模式：控制台模式")
else:
    print_info("运行模式：GUI 模式")

# 2. 核心依赖检测
print_header("2. 核心依赖检测")
check_module('requests', 'requests (HTTP 请求)')
check_module('prettytable', 'prettytable (表格格式化)')

# PySide6 是可选的
try:
    import PySide6
    print_success(f"PySide6: 已安装 (版本 {PySide6.__version__})")
    results['passed'] += 1
except ImportError:
    print_warning("PySide6: 未安装 (CLI 模式可用，GUI 模式不可用)")
    results['warnings'] += 1

try:
    import pypinyin
    print_success(f"pypinyin: 已安装 (车站拼音搜索)")
    results['passed'] += 1
except ImportError:
    print_warning("pypinyin: 未安装 (车站搜索功能受限)")
    results['warnings'] += 1

# 3. 项目模块检测
print_header("3. 项目模块检测")

# 添加项目根目录到路径
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

modules_to_check = [
    ('core.ticket_api', '票务 API 模块'),
    ('core.ticket_parser', '票务解析模块'),
    ('core.train_classifier', '车次分类模块'),
    ('core.time_filter', '时间筛选模块'),
    ('services.query_service', '查询服务模块'),
    ('services.export_service', '导出服务模块'),
    ('services.favorite_service', '收藏服务模块'),
    ('services.cache_service', '缓存服务模块'),
    ('services.station_search_service', '车站搜索服务'),
    ('services.monitor_manager', '监控任务管理'),
    ('notification.base', '通知基础模块'),
    ('notification.manager', '通知管理模块'),
    ('notification.channels', '通知渠道模块'),
    ('logger.ticket_logger', '日志记录模块'),
    ('logger.query_history', '查询历史模块'),
    ('config.config_manager', '配置管理模块'),
    ('ui.cli_menu', 'CLI 菜单模块'),
]

for module_name, display_name in modules_to_check:
    try:
        importlib.import_module(module_name)
        print_success(f"{display_name}: 正常")
        results['passed'] += 1
    except Exception as e:
        print_error(f"{display_name}: 异常 ({e})")
        results['failed'] += 1

# 4. 核心类检测
print_header("4. 核心类检测")

core_classes = [
    ('core.ticket_api', 'TicketAPI'),
    ('core.ticket_parser', 'TicketParser'),
    ('core.train_classifier', 'TrainClassifier'),
    ('services.query_service', 'QueryService'),
    ('services.favorite_service', 'FavoriteService'),
    ('services.cache_service', 'CacheService'),
    ('services.station_search_service', 'StationSearchService'),
    ('services.monitor_manager', 'MonitorManager'),
    ('notification.manager', 'NotificationManager'),
    ('config.config_manager', 'ConfigManager'),
    ('logger.ticket_logger', 'TicketLogger'),
    ('logger.query_history', 'QueryHistory'),
]

for module_name, class_name in core_classes:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, class_name):
            print_success(f"{class_name}: 可用")
            results['passed'] += 1
        else:
            print_error(f"{class_name}: 不存在于 {module_name}")
            results['failed'] += 1
    except Exception as e:
        print_error(f"{class_name} ({module_name}): 导入失败 ({e})")
        results['failed'] += 1

# 5. 数据文件检测
print_header("5. 数据文件检测")

files_to_check = [
    ('config.json', '配置文件'),
    ('station_codes.json', '车站数据'),
]

for file_path, description in files_to_check:
    full_path = os.path.join(project_dir, file_path)
    check_file(full_path, description)

# 6. 功能测试
print_header("6. 功能测试")

# 测试收藏服务
try:
    from services.favorite_service import FavoriteService
    test_file = os.path.join(project_dir, 'test_fav_temp.json')
    fav_service = FavoriteService(test_file)
    fav_service.add_favorite('G100')
    assert fav_service.is_favorite('G100'), "收藏判断失败"
    fav_service.remove_favorite('G100')
    os.remove(test_file)
    print_success("收藏服务功能：正常")
    results['passed'] += 1
except Exception as e:
    print_error(f"收藏服务功能：异常 ({e})")
    results['failed'] += 1

# 测试缓存服务
try:
    from services.cache_service import CacheService
    cache = CacheService(ttl_seconds=10)
    cache.set('北京', '上海', '2024-01-01', ['G1', 'G2'])
    result = cache.get('北京', '上海', '2024-01-01')
    assert result == ['G1', 'G2'], "缓存数据不匹配"
    print_success("缓存服务功能：正常")
    results['passed'] += 1
except Exception as e:
    print_error(f"缓存服务功能：异常 ({e})")
    results['failed'] += 1

# 测试车站搜索
try:
    from services.station_search_service import StationSearchService
    mock_dict = {'北京': 'BJP', '北京南': 'VNP', '上海': 'SHH'}
    search_service = StationSearchService(mock_dict)
    result = search_service.search_station('bj')
    if len(result) > 0:
        print_success("车站搜索功能：正常")
        results['passed'] += 1
    else:
        print_warning("车站搜索功能：无结果（可能数据不足）")
        results['warnings'] += 1
except Exception as e:
    print_error(f"车站搜索功能：异常 ({e})")
    results['failed'] += 1

# 测试监控任务管理器
try:
    from services.monitor_manager import MonitorManager
    manager = MonitorManager()
    task_id = manager.create_task('北京', '上海', '2024-01-01')
    assert len(task_id) > 0, "任务 ID 生成失败"
    manager.remove_task(task_id)
    print_success("监控任务管理：正常")
    results['passed'] += 1
except Exception as e:
    print_error(f"监控任务管理：异常 ({e})")
    results['failed'] += 1

# 7. GUI 模块检测（如果 PySide6 可用）
print_header("7. GUI 模块检测")

try:
    import PySide6
    print_success("PySide6: 已安装")

    gui_modules = [
        ('ui.gui.main_window', 'GUI 主窗口'),
    ]

    for module_name, display_name in gui_modules:
        try:
            importlib.import_module(module_name)
            print_success(f"{display_name}: 正常")
            results['passed'] += 1
        except Exception as e:
            print_error(f"{display_name}: 异常 ({e})")
            results['failed'] += 1

except ImportError:
    print_warning("PySide6 未安装，跳过 GUI 模块检测")
    results['warnings'] += 1

# 8. 配置检测
print_header("8. 配置检测")

try:
    import json
    config_path = os.path.join(project_dir, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 检查必要配置项
    required_keys = ['dc_classification', 'notification', 'logging']
    for key in required_keys:
        if key in config:
            print_success(f"配置项 {key}: 存在")
            results['passed'] += 1
        else:
            print_error(f"配置项 {key}: 缺失")
            results['failed'] += 1

    # 检查新增配置项
    if 'auto_open_12306' in config:
        print_success("auto_open_12306: 已配置")
        results['passed'] += 1
    else:
        print_warning("auto_open_12306: 未配置（将使用默认值）")
        results['warnings'] += 1

    if 'gui' in config:
        print_success("gui 配置：已配置")
        results['passed'] += 1
    else:
        print_warning("gui 配置：未配置（将使用默认值）")
        results['warnings'] += 1

except Exception as e:
    print_error(f"配置检测：异常 ({e})")
    results['failed'] += 1

# ============================================
# 汇总结果
# ============================================

print_header("检测结果汇总")

total = results['passed'] + results['failed'] + results['warnings']
pass_rate = (results['passed'] / total * 100) if total > 0 else 0

print(f"总检测项：{total}")
print(f"[OK] 通过：{results['passed']}")
print(f"[ERR] 失败：{results['failed']}")
print(f"[WARN] 警告：{results['warnings']}")
print(f"通过率：{pass_rate:.1f}%")

if results['failed'] == 0:
    print(f"\n恭喜！所有检测项均通过！")
    print(f"\n可以正常运行程序或打包为 exe")
elif results['failed'] <= 3:
    print(f"\n部分检测项失败，但不影响核心功能")
    print(f"\n建议修复失败项后再打包")
else:
    print(f"\n多个检测项失败，请先修复问题！")
    print(f"\n修复后请重新运行此检测脚本")

print()

# 退出码
sys.exit(0 if results['failed'] == 0 else 1)
