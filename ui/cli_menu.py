"""
CLI菜单模块
负责显示和处理命令行菜单
"""

import os
import sys
import time
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
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CLIMenu:
    """命令行菜单"""

    def __init__(self, logger, config_manager, query_service, query_history):
        """
        初始化菜单
        :param logger: 日志记录器
        :param config_manager: 配置管理器
        :param query_service: 查询服务
        :param query_history: 查询历史记录器
        """
        self.logger = logger
        self.config_manager = config_manager
        self.query_service = query_service
        self.query_history = query_history

    def show_main_menu(self) -> None:
        """启动主菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 ver 2.2.0 design by BH7GUL ===")
            print("="*65)
            print("\n启动主菜单")
            print("-" * 65)
            print("1. 开始新的查询")
            print("2. 修改默认配置")
            print("3. 查看查询历史")
            print("4. 通知设置")
            print("5. 退出程序")
            print("-" * 65)

            try:
                choice = input("请选择 (1-5): ").strip()
                if choice == '1':
                    self.start_query()
                elif choice == '2':
                    self.show_config_menu()
                elif choice == '3':
                    self.show_history()
                elif choice == '4':
                    self.show_notification_menu()
                elif choice == '5':
                    self.logger.info("用户退出程序")
                    print("\n程序已退出")
                    sys.exit(0)
                else:
                    print("\n[!] 无效选择，请重新输入")
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n程序已退出")
                sys.exit(0)

    def show_history(self) -> None:
        """查看查询历史"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 - 查询历史 ===")
        print("="*65)

        stats = self.query_history.get_statistics()
        records = self.query_history.get_recent(50)

        if not stats or stats['total_queries'] == 0:
            print("\n[!] 暂无查询历史")
            input("\n按回车键返回主菜单...")
            return

        print(f"\n【统计信息】")
        print(f"  总查询次数: {stats['total_queries']}")
        print(f"  有票查询次数: {stats['total_with_tickets']}")
        print(f"  有票率: {stats['total_with_tickets']/stats['total_queries']*100:.1f}%")

        if stats.get('top_trains'):
            print(f"\n【热门有票车次】（最近1000条）")
            for i, (train, count) in enumerate(stats['top_trains'][:10], 1):
                print(f"  {i}. {train}: {count} 次")

        print(f"\n【最近50次查询】")
        print("-" * 65)
        for i, rec in enumerate(reversed(records[:50]), 1):
            timestamp = rec['timestamp'].split('T')[1][:8] if 'T' in rec['timestamp'] else rec['timestamp']
            has_ticket = "✓" if rec['available_count'] > 0 else "✗"
            trains = ", ".join(rec['available_trains'][:3]) if rec['available_trains'] else "无"
            print(f"{i:2d}. [{timestamp}] {rec['from']:4s} -> {rec['to']:4s} ({rec['date']}) {has_ticket} {rec['available_count']:2d}车次 {trains}")

        input("\n按回车键返回主菜单...")

    def show_config_menu(self) -> None:
        """配置修改菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 - 配置修改 ===")
            print("="*65)
            print("\n配置修改菜单")
            print("-" * 65)

            config = self.config_manager.get_config()
            dc_mode = config["dc_classification"]["default_mode"]
            dc_mode_str = "official (官方)" if dc_mode == "official" else "smart (智能)"
            threshold = config["dc_classification"]["smart_threshold"]
            cooldown = config["notification"]["cooldown_seconds"]
            only_target = "是" if config["notification"]["only_target_trains"] else "否"
            min_tickets = config["notification"]["min_tickets"]

            print(f"1. 切换DC识别模式 (当前: {dc_mode_str})")
            print(f"2. 修改智能识别阈值 (当前: {threshold})")
            print(f"3. 修改通知冷却时间 (当前: {cooldown}秒)")
            print(f"4. 仅监控目标车次 (当前: {only_target})")
            print(f"5. 修改最小余票数量 (当前: {min_tickets})")
            print(f"6. 保存并返回")
            print("-" * 65)

            try:
                choice = input("请选择 (1-6): ").strip()
                config = self.config_manager.get_config()
                if choice == '1':
                    curr = config["dc_classification"]["default_mode"]
                    new_mode = "smart" if curr == "official" else "official"
                    config["dc_classification"]["default_mode"] = new_mode
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    self.logger.info(f"切换DC识别模式: {curr} -> {new_mode}")
                    print(f"\n[✓] DC识别模式已切换为: {new_mode}")
                    time.sleep(1)
                elif choice == '2':
                    try:
                        new_val = int(input("请输入新的阈值 (1-9999): ").strip())
                        if 1 <= new_val <= 9999:
                            config["dc_classification"]["smart_threshold"] = new_val
                            self.config_manager.set_config(config)
                            self.config_manager.save_config()
                            print(f"\n[✓] 智能识别阈值已修改为: {new_val}")
                        else:
                            print(f"\n[!] 阈值范围应为 1-9999")
                    except ValueError:
                        print(f"\n[!] 请输入有效数字")
                    time.sleep(1)
                elif choice == '3':
                    try:
                        new_val = int(input("请输入新的冷却时间(秒): ").strip())
                        if new_val >= 0:
                            config["notification"]["cooldown_seconds"] = new_val
                            self.config_manager.set_config(config)
                            self.config_manager.save_config()
                            print(f"\n[✓] 通知冷却时间已修改为: {new_val}秒")
                        else:
                            print(f"\n[!] 冷却时间不能为负数")
                    except ValueError:
                        print(f"\n[!] 请输入有效数字")
                    time.sleep(1)
                elif choice == '4':
                    curr = config["notification"]["only_target_trains"]
                    config["notification"]["only_target_trains"] = not curr
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    print(f"\n[✓] 仅监控目标车次已切换为: {'是' if not curr else '否'}")
                    time.sleep(1)
                elif choice == '5':
                    try:
                        new_val = int(input("请输入最小余票数量: ").strip())
                        if new_val >= 1:
                            config["notification"]["min_tickets"] = new_val
                            self.config_manager.set_config(config)
                            self.config_manager.save_config()
                            print(f"\n[✓] 最小余票数量已修改为: {new_val}")
                        else:
                            print(f"\n[!] 最小余票数量至少为1")
                    except ValueError:
                        print(f"\n[!] 请输入有效数字")
                    time.sleep(1)
                elif choice == '6':
                    self.config_manager.save_config()
                    print("\n[✓] 配置已保存")
                    time.sleep(1)
                    return
                else:
                    print("\n[!] 无效选择")
                    time.sleep(1)
            except KeyboardInterrupt:
                return

    def show_notification_menu(self) -> None:
        """通知设置菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 - 通知设置 ===")
            print("="*65)
            print("\n通知设置菜单")
            print("-" * 65)

            config = self.config_manager.get_config()
            channels = config.get("notification", {}).get("channels", {})

            win_enabled = channels.get("windows_desktop", {}).get("enabled", True)
            wx_enabled = channels.get("wechat_work", {}).get("enabled", False)
            feishu_enabled = channels.get("feishu", {}).get("enabled", False)
            ding_enabled = channels.get("dingtalk", {}).get("enabled", False)

            print(f"1. [{'√' if win_enabled else ' '}] Windows 原生通知")
            print(f"2. [{'√' if wx_enabled else ' '}] 企业微信机器人")
            print(f"3. [{'√' if feishu_enabled else ' '}] 飞书机器人")
            print(f"4. [{'√' if ding_enabled else ' '}] 钉钉机器人")
            print("5. 返回")
            print("-" * 65)

            try:
                choice = input("请选择 (1-5): ").strip()
                config = self.config_manager.get_config()
                channels = config.setdefault("notification", {}).setdefault("channels", {})
                if choice == '1':
                    channels.setdefault("windows_desktop", {})["enabled"] = not win_enabled
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    print(f"\n[✓] Windows 原生通知已{'启用' if not win_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '2':
                    channels.setdefault("wechat_work", {})["enabled"] = not wx_enabled
                    if not wx_enabled:
                        url = input("请输入企业微信机器人 Webhook URL: ").strip()
                        if url:
                            channels["wechat_work"]["webhook_url"] = url
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    print(f"\n[✓] 企业微信机器人已{'启用' if not wx_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '3':
                    channels.setdefault("feishu", {})["enabled"] = not feishu_enabled
                    if not feishu_enabled:
                        url = input("请输入飞书机器人 Webhook URL: ").strip()
                        if url:
                            channels["feishu"]["webhook_url"] = url
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    print(f"\n[✓] 飞书机器人已{'启用' if not feishu_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '4':
                    channels.setdefault("dingtalk", {})["enabled"] = not ding_enabled
                    if not ding_enabled:
                        url = input("请输入钉钉机器人 Webhook URL: ").strip()
                        secret = input("请输入钉钉机器人密钥: ").strip()
                        if url:
                            channels["dingtalk"]["webhook_url"] = url
                        if secret:
                            channels["dingtalk"]["secret"] = secret
                    self.config_manager.set_config(config)
                    self.config_manager.save_config()
                    print(f"\n[✓] 钉钉机器人已{'启用' if not ding_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '5':
                    return
                else:
                    print("\n[!] 无效选择")
                    time.sleep(1)
            except KeyboardInterrupt:
                return

    def start_query(self) -> None:
        """开始查询"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 ver 2.1.0 design by BH7GUL ===")
        print("="*65)

        from ui.filter_menu import FilterMenu

        f_st = input("1. 始发城市/站: ").strip()
        t_st = input("2. 到达城市/站: ").strip()
        date = input("3. 出发日期 (YYYY-MM-DD): ").strip()
        t_in = input("4. 监控车次 (回车全部): ").strip()
        target = t_in.split() if t_in else None

        # 更新通知管理器目标车次
        if self.query_service.notification_manager:
            self.query_service.notification_manager.config.target_trains = target
            if target:
                self.logger.info(f"仅监控目标车次: {target}")
            else:
                self.logger.info("监控所有车次")

        target_str = ', '.join(target) if target else '全部'
        self.logger.info(f"开始监控: {f_st} -> {t_st}, 日期: {date}, 目标车次: {target_str}")

        filters = {
            'type': None,
            'from': None,
            'to': None,
            'time_period': None,
            'sort': None
        }

        from msvcrt import kbhit, getch

        while True:
            # 显示查询状态
            print("\n正在查询车次信息...车次数量较多时可能需要一些时间，请耐心等待。")

            result = self.query_service.execute_query(date, f_st, t_st, target, filters)

            if result.get("error") == "STATION_NOT_FOUND":
                print(f"\n[!] 错误：无法识别站名。请检查是否输入了简写或错别字。")
                input("请按 [回车键] 重新开始查询...")
                return self.start_query()

            now = datetime.now().strftime("%H:%M:%S")
            os.system('cls' if os.name == 'nt' else 'clear')

            mode_str = "官方定义" if self.config_manager.get_config()["dc_classification"]["default_mode"] == "official" else "智能识别(动集归普)"
            print(f"[{now}] {f_st} -> {t_st} ({date}) | 模式: {mode_str}")
            print(f"当前筛选: 类型[{filters['type'] or '全部'}] | 始发[{filters['from'] or '全部'}] | 到达[{filters['to'] or '全部'}] | 时段[{filters['time_period'] if filters['time_period'] is None else {0: '00-06', 1: '06-12', 2: '12-18', 3: '18-24'}.get(filters['time_period'])}]")
            print("-" * 110)

            # 打印车次表格（立即显示）
            if result.get("table"):
                print(result["table"])

            # 显示统计信息
            total = result.get("total_count", 0)
            available = result.get("available_count", 0)
            filtered_count = len(result.get("all_tickets", []))
            print("-" * 110)
            print(f"【统计】共查询到 {total} 车次，当前显示 {filtered_count} 车次，其中 {available} 车次有票")

            print("\n[F]筛选排序  [M]切换模式  [E]导出结果  [R]重新查询  [Q]退出")

            wait_sec = 180
            for i in range(wait_sec, 0, -1):
                print(f"\r{i}s 后刷新... (Enter立即刷新)", end="", flush=True)
                if kbhit():
                    key = getch().lower()
                    if key == b'\r':
                        self.logger.debug("用户手动触发刷新")
                        break
                    if key == b'f':
                        should_continue, filters = FilterMenu.show_filter_menu(filters, result.get("all_tickets"))
                        break
                    if key == b'm':
                        config = self.config_manager.get_config()
                        curr = config["dc_classification"]["default_mode"]
                        config["dc_classification"]["default_mode"] = "smart" if curr == "official" else "official"
                        self.config_manager.set_config(config)
                        self.config_manager.save_config()
                        new_mode = config["dc_classification"]["default_mode"]
                        self.logger.info(f"切换DC识别模式: {curr} -> {new_mode}")
                        break
                    if key == b'e' and result.get("all_tickets"):
                        from services.export_service import ExportService
                        log_dir = os.path.join(get_base_dir(), "logs")
                        os.makedirs(log_dir, exist_ok=True)
                        export_file = os.path.join(log_dir, f"tickets_{date}_{datetime.now().strftime('%H%M%S')}.json")
                        ExportService.export_to_json(result["all_tickets"], export_file)
                        print(f"\n[✓] 结果已导出到: {export_file}")
                        input("按回车键继续...")
                        break
                    if key == b'r':
                        self.logger.info("用户重新开始查询")
                        return self.start_query()
                    if key == b'q':
                        self.logger.info("用户退出程序")
                        sys.exit()
                time.sleep(1)
