"""
12306余票监控工具 - 主程序
版本: 2.1.0
设计: BH7GUL
"""

import os
import sys
import atexit
from datetime import datetime


def get_base_dir():
    """
    获取程序基础目录
    - 开发环境: 返回脚本所在目录
    - 打包环境: 返回exe所在目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的exe环境
        return os.path.dirname(sys.executable)
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """
    获取资源文件路径
    - 开发环境: 返回源码目录下的路径
    - 打包环境: 返回临时解压目录下的路径（PyInstaller内部资源）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后，资源文件在临时目录
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def main():
    """主程序入口"""
    # 获取程序基础目录（exe所在目录或源码目录）
    base_dir = get_base_dir()
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 初始化日志系统
    from logger import TicketLogger, QueryHistory
    logger = TicketLogger(log_dir, {})
    logger.log_startup("2.1.0")

    # 初始化查询历史
    query_history = QueryHistory(log_dir)

    # 初始化配置管理器 - 配置文件放在exe同目录，方便用户修改
    config_json = os.path.join(base_dir, "config.json")
    from config.config_manager import ConfigManager
    config_manager = ConfigManager(config_json)

    # 初始化车站数据 - 车站数据放在exe同目录
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
            notification_manager.register_channel(NativeWindowsNotification())
            logger.info("通知渠道已启用: Windows原生通知")
    except Exception as e:
        logger.error(f"通知系统初始化失败: {e}", exc_info=True)

    # 初始化查询服务
    from services.query_service import QueryService
    query_service = QueryService(
        ticket_api=ticket_api,
        ticket_parser=ticket_parser,
        train_classifier=train_classifier,
        logger=logger,
        query_history=query_history,
        notification_manager=notification_manager,
        config_manager=config_manager
    )

    # 注册退出处理
    def cleanup():
        try:
            logger.log_shutdown()
        except:
            pass

    atexit.register(cleanup)

    # 启动主菜单
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


if __name__ == "__main__":
    if os.name == 'nt':
        os.system('')
    main()
