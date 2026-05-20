"""
12306 余票监控工具 - 主程序
版本：3.2.0
设计：BH7GUL
"""

import os
import sys
import atexit
from datetime import datetime


def get_base_dir():
    """
    获取程序基础目录
    - 开发环境：返回脚本所在目录
    - 打包环境：返回 exe 所在目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的 exe 环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    获取资源文件路径
    - 开发环境：返回源码目录下的路径
    - 打包环境：返回临时解压目录下的路径（PyInstaller 内部资源）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，资源文件在临时目录
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def has_console():
    """检查是否有控制台窗口"""
    try:
        # 尝试访问 stdin，如果有控制台则不会失败
        sys.stdin.fileno()
        return True
    except (AttributeError, OSError):
        return False


def main():
    """主程序入口"""
    # 获取程序基础目录（exe 所在目录或源码目录）
    base_dir = get_base_dir()
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 初始化日志系统
    from logger import TicketLogger, QueryHistory
    logger = TicketLogger(log_dir, {})
    logger.log_startup("3.2.0")

    # 初始化查询历史
    query_history = QueryHistory(log_dir)

    # 初始化配置管理器 - 配置文件放在 exe 同目录，方便用户修改
    config_json = os.path.join(base_dir, "config.json")
    from config.config_manager import ConfigManager
    config_manager = ConfigManager(config_json)

    # 初始化车站数据 - 车站数据放在 exe 同目录
    station_json = os.path.join(base_dir, "station_codes.json")
    from core.ticket_api import TicketAPI
    ticket_api = TicketAPI(station_json, logger)
    ticket_api.init_station_data()

    # 初始化车次分类器
    from core.train_classifier import TrainClassifier
    train_classifier = TrainClassifier()

    # 初始化票务解析器
    from core.ticket_parser import TicketParser
    ticket_parser = TicketParser()

    # 初始化通知系统
    notification_manager = None
    from notification import NotificationManager, NativeWindowsNotification
    from notification.channels import WeChatWorkNotification, FeishuNotification, DingTalkNotification
    try:
        notif_config = config_manager.get_config().get("notification", {})
        if notif_config.get("enabled", True):
            # 图标资源从打包内部获取
            icon_path = get_resource_path("railway.ico")
            notif_config_filtered = {
                'enabled': notif_config.get('enabled', True),
                'cooldown_seconds': notif_config.get('cooldown_seconds', 300),
                'only_target_trains': notif_config.get('only_target_trains', False),
                'min_tickets': notif_config.get('min_tickets', 1),
                'target_trains': None
            }
            notification_manager = NotificationManager(notif_config_filtered)

            # 根据配置注册通知渠道
            channels_cfg = notif_config.get("channels", {})

            # Windows 原生通知
            if channels_cfg.get("windows_desktop", {}).get("enabled", True):
                notification_manager.register_channel(NativeWindowsNotification())
                logger.info("通知渠道已启用：Windows 原生通知")

            # 企业微信
            wx_cfg = channels_cfg.get("wechat_work", {})
            if wx_cfg.get("enabled") and wx_cfg.get("webhook_url"):
                notification_manager.register_channel(WeChatWorkNotification(wx_cfg["webhook_url"]))
                logger.info("通知渠道已启用：企业微信")

            # 飞书
            fs_cfg = channels_cfg.get("feishu", {})
            if fs_cfg.get("enabled") and fs_cfg.get("webhook_url"):
                notification_manager.register_channel(FeishuNotification(fs_cfg["webhook_url"]))
                logger.info("通知渠道已启用：飞书")

            # 钉钉
            dd_cfg = channels_cfg.get("dingtalk", {})
            if dd_cfg.get("enabled") and dd_cfg.get("webhook_url"):
                notification_manager.register_channel(
                    DingTalkNotification(dd_cfg["webhook_url"], dd_cfg.get("secret"))
                )
                logger.info("通知渠道已启用：钉钉")
    except Exception as e:
        logger.error(f"通知系统初始化失败：{e}", exc_info=True)

    # 初始化缓存服务
    from services.cache_service import CacheService
    cache_service = CacheService(ttl_seconds=10)

    # 初始化收藏服务
    favorites_json = os.path.join(base_dir, "favorites.json")
    from services.favorite_service import FavoriteService
    favorite_service = FavoriteService(favorites_json)

    # 初始化车站搜索服务
    from services.station_search_service import StationSearchService
    station_search_service = StationSearchService(ticket_api.station_dict)

    # 初始化监控任务管理器
    from services.monitor_manager import MonitorManager
    monitor_manager = MonitorManager()

    # 初始化查询服务
    from services.query_service import QueryService
    query_service = QueryService(
        ticket_api=ticket_api,
        ticket_parser=ticket_parser,
        train_classifier=train_classifier,
        logger=logger,
        query_history=query_history,
        notification_manager=notification_manager,
        config_manager=config_manager,
        cache_service=cache_service
    )

    # 注册退出处理
    def cleanup():
        try:
            logger.log_shutdown()
        except:
            pass
        # 停止所有监控任务
        try:
            monitor_manager.stop_all_tasks()
        except:
            pass

    atexit.register(cleanup)

    # 检查启动参数和运行环境
    # --gui: 启动 GUI 界面
    # --cli: 启动 CLI 界面
    # 默认：GUI 模式（如果没有控制台）或 CLI 模式（如果有控制台）

    use_gui = None

    if len(sys.argv) > 1:
        if sys.argv[1] == '--gui':
            use_gui = True
        elif sys.argv[1] == '--cli':
            use_gui = False

    if use_gui is None:
        # 默认启动 GUI 模式
        use_gui = True
        # 只有显式传入 --cli 参数才启动 CLI
        if len(sys.argv) > 1 and sys.argv[1] == '--cli':
            use_gui = False

    if use_gui:
        # 启动 GUI 模式
        logger.info("启动 GUI 模式")
        start_gui(
            query_service=query_service,
            config_manager=config_manager,
            favorite_service=favorite_service,
            cache_service=cache_service,
            station_search_service=station_search_service,
            monitor_manager=monitor_manager,
            logger=logger
        )
    else:
        # 启动 CLI 模式
        logger.info("启动 CLI 模式")
        from ui.cli_menu import CLIMenu
        cli_menu = CLIMenu(
            logger=logger,
            config_manager=config_manager,
            query_service=query_service,
            query_history=query_history
        )

        try:
            cli_menu.show_main_menu()
        except KeyboardInterrupt:
            print("\n程序已退出")
            sys.exit(0)


def start_gui(query_service, config_manager, favorite_service, cache_service,
              station_search_service, monitor_manager, logger):
    """启动 GUI 界面"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from ui.gui.main_window import MainWindow

    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("12306 余票监控工具")
    app.setApplicationVersion("3.2.0")

    # 设置应用样式
    app.setStyle("Fusion")

    window = MainWindow(
        query_service=query_service,
        config_manager=config_manager,
        favorite_service=favorite_service,
        cache_service=cache_service,
        station_search_service=station_search_service,
        monitor_manager=monitor_manager,
        logger=logger
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    if os.name == 'nt':
        os.system('')
    main()
