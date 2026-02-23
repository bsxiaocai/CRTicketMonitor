import requests
import time
import re
import json
import os
import sys
import msvcrt
import atexit
from datetime import datetime
from prettytable import PrettyTable # 表格显示

# 日志与通知模块
from logger import TicketLogger, QueryHistory  # 日志记录和查询历史
from notification import NotificationManager, NativeWindowsNotification, TicketInfo # 通知管理器和票务信息类


class TrainMonitor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.station_json = os.path.join(base_dir, "station_codes.json")
        self.config_json = os.path.join(base_dir, "config.json")
        self.log_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # 新增：初始化日志
        self.logger = TicketLogger(self.log_dir, {})
        self.logger.log_startup("2.0.0")

        # 新增：初始化查询历史记录
        self.query_history = QueryHistory(self.log_dir)

        self.station_dict = {}
        self.code_to_name = {}
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        }

        # 默认配置（扩展）
        self.config = {
            "dc_classification": {
                "default_mode": "official",
                "smart_threshold": 899,
                "custom_mapping": {}
            },
            "notification": {
                "enabled": True,
                "cooldown_seconds": 300,
                "only_target_trains": False,
                "min_tickets": 1
            },
            "logging": {
                "level": "INFO",
                "max_size_mb": 10,
                "backup_count": 5,
                "console_output": False,
                "log_query_history": True
            }
        }

        self.load_config()
        self.init_station_data()

        # 新增：初始化通知管理器
        self.notification_manager = None
        self._setup_notifications()

        # 注册退出处理
        atexit.register(self._cleanup)

    def _cleanup(self):
        """程序退出时的清理工作"""
        try:
            self.logger.log_shutdown()
        except:
            pass

    def _setup_notifications(self):
        """初始化通知系统"""
        try:
            notif_config = self.config.get("notification", {})
            if notif_config.get("enabled", True):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(base_dir, "railway.ico")

                # 过滤配置，只传递 NotificationConfig 定义的参数
                notif_config_filtered = {
                    'enabled': notif_config.get('enabled', True),
                    'cooldown_seconds': notif_config.get('cooldown_seconds', 300),
                    'only_target_trains': notif_config.get('only_target_trains', False),
                    'min_tickets': notif_config.get('min_tickets', 1),
                    'target_trains': None  # 初始为空
                }
                self.notification_manager = NotificationManager(notif_config_filtered)

                # 直接使用 Windows 原生通知（无需外部依赖）
                self.notification_manager.register_channel(NativeWindowsNotification())
                self.logger.info("通知渠道已启用: Windows原生通知")
        except Exception as e:
            self.logger.error(f"通知系统初始化失败: {e}", exc_info=True)

    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_json):
            try:
                with open(self.config_json, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # 深度合并配置，保持默认值
                    self._deep_update(self.config, loaded_config)
                    self.logger.debug(f"配置文件已加载: {self.config_json}")
            except Exception as e:
                self.logger.error(f"配置文件读取失败，使用默认配置: {e}", exc_info=True)
        else:
            self.logger.debug(f"配置文件不存在，使用默认配置: {self.config_json}")
            # 保存默认配置
            self.save_config()

    def _deep_update(self, d, u):
        """深度合并字典"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_json, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            self.logger.debug(f"配置文件已保存: {self.config_json}")
        except Exception as e:
            self.logger.error(f"配置文件保存失败: {e}", exc_info=True)

    def init_station_data(self):
        """同步车站编码数据"""
        try:
            self.logger.debug("开始同步车站数据")
            url = f'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?v={time.time()}'
            res = self.session.get(url, timeout=10)
            matched = re.findall(r'([\u4e00-\u9fa5]+)\|([A-Z]+)', res.text)
            if matched:
                self.station_dict = {name: code for name, code in matched}
                with open(self.station_json, "w", encoding="utf-8") as f:
                    json.dump(self.station_dict, f, ensure_ascii=False, indent=4)
                self.logger.debug(f"车站数据同步完成，共 {len(self.station_dict)} 个站点")
        except Exception as e:
            self.logger.warning(f"车站数据同步失败，使用缓存: {e}")
            if os.path.exists(self.station_json):
                try:
                    with open(self.station_json, "r", encoding="utf-8") as f:
                        self.station_dict = json.load(f)
                        self.logger.debug(f"使用缓存车站数据，共 {len(self.station_dict)} 个站点")
                except Exception as e:
                    self.logger.error(f"读取缓存车站数据失败: {e}", exc_info=True)

        self.code_to_name = {code: name for name, code in self.station_dict.items()}

    ### 对C/D字头的智能识别逻辑（国铁对动力集中型动车组列车的定义差异） ###
    def classify_train(self, train_no):
        """后台判断逻辑"""
        conf = self.config["dc_classification"]
        if train_no in conf.get("custom_mapping", {}):
            return conf["custom_mapping"][train_no]

        prefix = train_no[0].upper()
        num_part = re.search(r'\d+', train_no)
        number = int(num_part.group()) if num_part else 9999

        if prefix in ['K', 'T', 'Z'] or train_no.isdigit():
            return "普通车"
        if prefix == 'G':
            return "高铁动车"
        if prefix in ['D', 'C']:
            if conf.get("default_mode") == "official":
                return "高铁动车"
            return "普通车" if number <= conf.get("smart_threshold", 899) else "高铁动车"
        return "其他"

    def filter_by_time_period(self, departure_time, period):
        """
        时段筛选（模仿12306）
        将一天分为4个时段：00:00-06:00, 06:00-12:00, 12:00-18:00, 18:00-24:00
        :param departure_time: 车次发车时间（格式：HH:MM）
        :param period: 时段（None=全部, 0=00:00-06:00, 1=06:00-12:00, 2=12:00-18:00, 3=18:00-24:00）
        :return: 是否保留该车次
        """
        if period is None:
            return True  # 不筛选
        try:
            hour = int(departure_time.split(':')[0])
            if period == 0:
                return 0 <= hour < 6
            elif period == 1:
                return 6 <= hour < 12
            elif period == 2:
                return 12 <= hour < 18
            elif period == 3:
                return 18 <= hour < 24
            return False
        except:
            return True  # 解析失败时保留

    def sort_tickets(self, tickets_with_data, sort_type):
        """
        排序功能
        :param tickets_with_data: [(TicketInfo, raw_data), ...]
        :param sort_type: 排序类型
            'earliest_depart' - 最早发车
            'latest_depart' - 最晚发车
            'earliest_arrival' - 最早到达
            'latest_arrival' - 最晚到达
            'shortest' - 最短历时
            'longest' - 最长历时
        :return: 排序后的列表
        """
        def time_to_minutes(t):
            """将 HH:MM 格式转换为分钟数"""
            try:
                h, m = map(int, t.split(':'))
                return h * 60 + m
            except:
                return 99999  # 解析失败放在最后

        def duration_to_minutes(d):
            """将历时转换为分钟数（支持跨天）"""
            try:
                h, m = map(int, d.split(':'))
                return h * 60 + m
            except:
                return 99999

        if sort_type == 'earliest_depart':
            return sorted(tickets_with_data, key=lambda x: time_to_minutes(x[1][8]))
        elif sort_type == 'latest_depart':
            return sorted(tickets_with_data, key=lambda x: time_to_minutes(x[1][8]), reverse=True)
        elif sort_type == 'earliest_arrival':
            return sorted(tickets_with_data, key=lambda x: time_to_minutes(x[1][9]))
        elif sort_type == 'latest_arrival':
            return sorted(tickets_with_data, key=lambda x: time_to_minutes(x[1][9]), reverse=True)
        elif sort_type == 'shortest':
            return sorted(tickets_with_data, key=lambda x: duration_to_minutes(x[1][10]))
        elif sort_type == 'longest':
            return sorted(tickets_with_data, key=lambda x: duration_to_minutes(x[1][10]), reverse=True)
        return tickets_with_data  # 无排序

    def query_tickets(self, date, from_station, to_station):
        """执行查询，站名匹配失败则强制同步"""
        if from_station not in self.station_dict or to_station not in self.station_dict:
            self.logger.debug(f"站名不在字典中，尝试重新同步: {from_station} -> {to_station}")
            self.init_station_data()

        from_code = self.station_dict.get(from_station)
        to_code = self.station_dict.get(to_station)

        if not from_code or not to_code:
            self.logger.error(f"站名匹配失败: {from_station}({from_code}) -> {to_station}({to_code})")
            return "STATION_NOT_FOUND"

        url = f"https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
        try:
            self.session.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=self.headers, timeout=5)
            response = self.session.get(url, headers=self.headers, timeout=10)
            result = response.json().get('data', {}).get('result', [])
            self.logger.debug(f"查询完成: {from_station} -> {to_station}, 返回 {len(result)} 条记录")
            return result
        except Exception as e:
            self.logger.error(f"查询请求失败: {e}", exc_info=True)
            return None

    def export_to_json(self, tickets, filepath: str):
        """
        导出车票信息到 JSON 文件
        :param tickets: 车票列表
        :param filepath: 输出文件路径
        """
        data = {
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_count": len(tickets),
            "tickets": [ticket.to_dict() for ticket in tickets]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"导出 {len(tickets)} 条车票信息到: {filepath}")

    def parse_and_print(self, raw_data, target_trains=None, type_filter=None, sel_from=None, sel_to=None, date=None, return_all=False, time_period=None, sort_type=None):
        """
        解析并打印车票信息
        :param return_all: 是否返回所有车票（包括无票的）
        :param time_period: 时段筛选（None=全部, 0=00:00-06:00, 1=06:00-12:00, 2=12:00-18:00, 3=18:00-24:00）
        :param sort_type: 排序类型（'earliest_depart', 'latest_depart', 'earliest_arrival', 'latest_arrival', 'shortest', 'longest', None=不排序）
        :return: 有票的车次列表；如果 return_all=True，返回所有车票
        """
        table = PrettyTable()
        table.field_names = ["车次", "始发", "到达", "开点", "到点", "历时", "商/特", "一等座", "二等座", "一等/软卧", "二等/硬卧", "软座", "硬座", "无座"]

        available_tickets = []  # 记录有票的车次
        all_tickets = []  # 记录所有车票
        temp_all = []  # 临时存储所有待处理的（ticket_info, raw_data, row）元组

        for item in raw_data:
            d = item.split('|')
            train_no = d[3]
            train_type = self.classify_train(train_no)

            if type_filter and type_filter not in train_type: continue
            if target_trains and train_no not in target_trains: continue

            f_st_name = self.code_to_name.get(d[6], d[6])
            t_st_name = self.code_to_name.get(d[7], d[7])
            if sel_from and f_st_name != sel_from: continue
            if sel_to and t_st_name != sel_to: continue

            # 时段筛选
            if not self.filter_by_time_period(d[8], time_period):
                continue

            # 坐席解析
            sw = d[32] or "--"   # 商务/特等
            yd = d[31] or "--"   # 一等座
            ed = d[30] or "--"   # 二等座
            y_wo = d[23] or "--" # 一等卧/软卧
            e_wo = d[28] or "--" # 二等卧/硬卧
            rz = d[24] or "--"   # 软座
            yz = d[29] or "--"   # 硬座
            wz = d[26] or "--"   # 无座

            row = [train_no, f_st_name, t_st_name, d[8], d[9], d[10], sw, yd, ed, y_wo, e_wo, rz, yz, wz]

            # 坐席信息
            seats = {'商/特': sw, '一等座': yd, '二等座': ed,
                     '一等/软卧': y_wo, '二等/硬卧': e_wo, '软座': rz, '硬座': yz, '无座': wz}

            # 基础着色逻辑（非S字头：有任意票即绿）
            has_ticket = any(s not in ['无', '--', '', '0'] for s in [sw, yd, ed, y_wo, e_wo, rz, yz])

            # S字头特殊逻辑
            if train_no.upper().startswith('S'):
                is_green = False
                ed_has = ed not in ['无', '--', '', '0']
                wz_has = wz not in ['无', '--', '', '0']

                # 情况1: 有二等座或无座席位，且任一有票
                if (ed != "--" or wz != "--") and (ed_has or wz_has):
                    is_green = True
                # 情况2: 只有无座席位且有票
                elif (ed == "--" and yd == "--" and rz == "--" and wz != "--") and wz_has:
                    is_green = True

                if is_green:
                    row[0] = f"\033[92m{train_no}\033[0m"
            else:
                if has_ticket:
                    row[0] = f"\033[92m{train_no}\033[0m"

            # 为所有车次创建 TicketInfo（用于导出）
            available_seats = {k: v for k, v in seats.items() if v not in ['无', '--', '', '0']}
            if date:
                ticket_info = TicketInfo(
                    train_no=train_no,
                    from_station=f_st_name,
                    to_station=t_st_name,
                    date=date,
                    departure_time=d[8],
                    duration=d[10],
                    available_seats=available_seats if has_ticket else {}
                )
                all_tickets.append(ticket_info)

                # 有票的车次单独记录
                if has_ticket:
                    available_tickets.append(ticket_info)

            # 保存原始数据用于排序
            temp_all.append((ticket_info, d, row))

        # 排序（如果有排序需求）
        if sort_type:
            temp_all = self.sort_tickets(temp_all, sort_type)

        # 添加到表格
        for _, _, row in temp_all:
            table.add_row(row)
        print(table)
        return all_tickets if return_all else available_tickets  # 根据参数返回

    def show_main_menu(self):
        """启动主菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 ver 2.0 design by BH7GUL ===")
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

    def show_history(self):
        """查看查询历史"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 - 查询历史 ===")
        print("="*65)

        # 获取历史记录和统计信息
        stats = self.query_history.get_statistics()
        records = self.query_history.get_recent(50)

        if not stats or stats['total_queries'] == 0:
            print("\n[!] 暂无查询历史")
            input("\n按回车键返回主菜单...")
            return

        # 显示统计信息
        print(f"\n【统计信息】")
        print(f"  总查询次数: {stats['total_queries']}")
        print(f"  有票查询次数: {stats['total_with_tickets']}")
        print(f"  有票率: {stats['total_with_tickets']/stats['total_queries']*100:.1f}%")

        if stats.get('top_trains'):
            print(f"\n【热门有票车次】（最近1000条）")
            for i, (train, count) in enumerate(stats['top_trains'][:10], 1):
                print(f"  {i}. {train}: {count} 次")

        # 显示最近查询记录
        print(f"\n【最近50次查询】")
        print("-" * 65)
        for i, rec in enumerate(reversed(records[:50]), 1):
            timestamp = rec['timestamp'].split('T')[1][:8] if 'T' in rec['timestamp'] else rec['timestamp']
            has_ticket = "✓" if rec['available_count'] > 0 else "✗"
            trains = ", ".join(rec['available_trains'][:3]) if rec['available_trains'] else "无"
            print(f"{i:2d}. [{timestamp}] {rec['from']:4s} -> {rec['to']:4s} ({rec['date']}) {has_ticket} {rec['available_count']:2d}车次 {trains}")

        input("\n按回车键返回主菜单...")

    def show_config_menu(self):
        """配置修改菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 - 配置修改 ===")
            print("="*65)
            print("\n配置修改菜单")
            print("-" * 65)

            dc_mode = self.config["dc_classification"]["default_mode"]
            dc_mode_str = "official (官方)" if dc_mode == "official" else "smart (智能)"
            threshold = self.config["dc_classification"]["smart_threshold"]
            cooldown = self.config["notification"]["cooldown_seconds"]
            only_target = "是" if self.config["notification"]["only_target_trains"] else "否"
            min_tickets = self.config["notification"]["min_tickets"]

            print(f"1. 切换DC识别模式 (当前: {dc_mode_str})")
            print(f"2. 修改智能识别阈值 (当前: {threshold})")
            print(f"3. 修改通知冷却时间 (当前: {cooldown}秒)")
            print(f"4. 仅监控目标车次 (当前: {only_target})")
            print(f"5. 修改最小余票数量 (当前: {min_tickets})")
            print(f"6. 保存并返回")
            print("-" * 65)

            try:
                choice = input("请选择 (1-6): ").strip()
                if choice == '1':
                    curr = self.config["dc_classification"]["default_mode"]
                    new_mode = "smart" if curr == "official" else "official"
                    self.config["dc_classification"]["default_mode"] = new_mode
                    self.save_config()
                    self.logger.info(f"切换DC识别模式: {curr} -> {new_mode}")
                    print(f"\n[✓] DC识别模式已切换为: {new_mode}")
                    time.sleep(1)
                elif choice == '2':
                    try:
                        new_val = int(input("请输入新的阈值 (1-9999): ").strip())
                        if 1 <= new_val <= 9999:
                            self.config["dc_classification"]["smart_threshold"] = new_val
                            self.save_config()
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
                            self.config["notification"]["cooldown_seconds"] = new_val
                            self.save_config()
                            print(f"\n[✓] 通知冷却时间已修改为: {new_val}秒")
                        else:
                            print(f"\n[!] 冷却时间不能为负数")
                    except ValueError:
                        print(f"\n[!] 请输入有效数字")
                    time.sleep(1)
                elif choice == '4':
                    curr = self.config["notification"]["only_target_trains"]
                    self.config["notification"]["only_target_trains"] = not curr
                    self.save_config()
                    print(f"\n[✓] 仅监控目标车次已切换为: {'是' if not curr else '否'}")
                    time.sleep(1)
                elif choice == '5':
                    try:
                        new_val = int(input("请输入最小余票数量: ").strip())
                        if new_val >= 1:
                            self.config["notification"]["min_tickets"] = new_val
                            self.save_config()
                            print(f"\n[✓] 最小余票数量已修改为: {new_val}")
                        else:
                            print(f"\n[!] 最小余票数量至少为1")
                    except ValueError:
                        print(f"\n[!] 请输入有效数字")
                    time.sleep(1)
                elif choice == '6':
                    self.save_config()
                    print("\n[✓] 配置已保存")
                    time.sleep(1)
                    return
                else:
                    print("\n[!] 无效选择")
                    time.sleep(1)
            except KeyboardInterrupt:
                return

    def show_notification_menu(self):
        """通知设置菜单"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 - 通知设置 ===")
            print("="*65)
            print("\n通知设置菜单")
            print("-" * 65)

            notif_conf = self.config["notification"]
            channels = notif_conf.get("channels", {})

            # Windows 原生通知
            win_enabled = channels.get("windows_desktop", {}).get("enabled", True)
            print(f"1. [{'√' if win_enabled else ' '}] Windows 原生通知")

            # 企业微信
            wx_enabled = channels.get("wechat_work", {}).get("enabled", False)
            print(f"2. [{'√' if wx_enabled else ' '}] 企业微信机器人")

            # 飞书
            feishu_enabled = channels.get("feishu", {}).get("enabled", False)
            print(f"3. [{'√' if feishu_enabled else ' '}] 飞书机器人")

            # 钉钉
            ding_enabled = channels.get("dingtalk", {}).get("enabled", False)
            print(f"4. [{'√' if ding_enabled else ' '}] 钉钉机器人")

            print("5. 返回")
            print("-" * 65)

            try:
                choice = input("请选择 (1-5): ").strip()
                if choice == '1':
                    channels.setdefault("windows_desktop", {})["enabled"] = not win_enabled
                    self.save_config()
                    print(f"\n[✓] Windows 原生通知已{'启用' if not win_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '2':
                    channels.setdefault("wechat_work", {})["enabled"] = not wx_enabled
                    if not wx_enabled:
                        url = input("请输入企业微信机器人 Webhook URL: ").strip()
                        if url:
                            channels["wechat_work"]["webhook_url"] = url
                    self.save_config()
                    print(f"\n[✓] 企业微信机器人已{'启用' if not wx_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '3':
                    channels.setdefault("feishu", {})["enabled"] = not feishu_enabled
                    if not feishu_enabled:
                        url = input("请输入飞书机器人 Webhook URL: ").strip()
                        if url:
                            channels["feishu"]["webhook_url"] = url
                    self.save_config()
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
                    self.save_config()
                    print(f"\n[✓] 钉钉机器人已{'启用' if not ding_enabled else '禁用'}")
                    time.sleep(1)
                elif choice == '5':
                    return
                else:
                    print("\n[!] 无效选择")
                    time.sleep(1)
            except KeyboardInterrupt:
                return

    def show_filter_menu(self, current_filters, data=None):
        """
        二级筛选菜单
        :param current_filters: dict 包含当前筛选状态 {'type': ..., 'from': ..., 'to': ..., 'time_period': ..., 'sort': ...}
        :param data: 车次原始数据（可选），用于获取车站列表
        :return: tuple (should_continue, updated_filters)
        """
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*80)
            print("=== 筛选与排序菜单 ===")
            print("="*80)

            # 显示当前筛选状态
            type_str = current_filters['type'] or '全部'
            from_str = current_filters['from'] or '全部'
            to_str = current_filters['to'] or '全部'
            period_map = {None: '全部时段', 0: '00:00-06:00', 1: '06:00-12:00', 2: '12:00-18:00', 3: '18:00-24:00'}
            period_str = period_map.get(current_filters['time_period'], '全部时段')
            sort_map = {
                None: '无', 'earliest_depart': '最早发车', 'latest_depart': '最晚发车',
                'earliest_arrival': '最早到达', 'latest_arrival': '最晚到达',
                'shortest': '最短历时', 'longest': '最长历时'
            }
            sort_str = sort_map.get(current_filters['sort'], '无')

            print(f"\n【当前筛选】")
            print(f"  车型: {type_str} | 始发: {from_str} | 到达: {to_str}")
            print(f"  时段: {period_str} | 排序: {sort_str}")
            print("-" * 80)

            # 显示菜单选项
            print("[车型筛选]  1.全部  2.高铁动车  3.普通车")
            print("[站点筛选]  4.始发站  5.到达站")
            print("[时段筛选]  6.全部时段  7.00:00-06:00  8.06:00-12:00  9.12:00-18:00  0.18:00-24:00")
            print("[排序选项]  A.最早发车  B.最晚发车  C.最早到达  D.最晚到达  E.最短历时  F.最长历时")
            print("[其他]      R.重置筛选  X.返回主查询")
            print("-" * 80)

            try:
                choice = input("请输入选项 (1-9, 0, A-F, R, X): ").strip().lower()

                # 车型筛选 (1-3)
                if choice == '1':
                    current_filters['type'] = None
                    print("\n[✓] 车型筛选已重置为：全部")
                    time.sleep(0.5)
                elif choice == '2':
                    current_filters['type'] = "高铁动车"
                    print("\n[✓] 车型筛选已设置为：高铁动车")
                    time.sleep(0.5)
                elif choice == '3':
                    current_filters['type'] = "普通车"
                    print("\n[✓] 车型筛选已设置为：普通车")
                    time.sleep(0.5)

                # 站点筛选 (4-5)
                elif choice == '4':
                    if data:
                        # 列出所有始发站
                        all_from_stations = sorted(list(set(self.code_to_name.get(x.split('|')[6], x.split('|')[6]) for x in data)))
                        print("\n" + "=" * 40)
                        print("【始发站列表】")
                        print("=" * 40)
                        for i, station in enumerate(all_from_stations, 1):
                            print(f"{i:2d}. {station}", end="  " if i % 4 != 0 else "\n")
                        print("\n" + "-" * 40)
                        print("[提示] 直接按回车表示'全部'，不进行该项筛选")
                        try:
                            idx_input = input("输入序号选择（按回车跳过）: ").strip()
                            if idx_input:
                                idx = int(idx_input)
                                if 1 <= idx <= len(all_from_stations):
                                    new_from = all_from_stations[idx - 1]
                                else:
                                    print("\n[!] 序号超出范围")
                                    time.sleep(0.5)
                                    continue
                            else:
                                new_from = None
                        except (ValueError, IndexError):
                            print("\n[!] 无效输入")
                            time.sleep(0.5)
                            continue
                    else:
                        print("\n[提示] 直接按回车表示'全部'，不进行该项筛选")
                        new_from = input("输入精确始发站（按回车键跳过）: ").strip()
                    current_filters['from'] = new_from if new_from else None
                    print(f"\n[✓] 始发站筛选已设置为：{new_from if new_from else '全部'}")
                    time.sleep(0.5)
                elif choice == '5':
                    if data:
                        # 列出所有到达站
                        all_to_stations = sorted(list(set(self.code_to_name.get(x.split('|')[7], x.split('|')[7]) for x in data)))
                        print("\n" + "=" * 40)
                        print("【到达站列表】")
                        print("=" * 40)
                        for i, station in enumerate(all_to_stations, 1):
                            print(f"{i:2d}. {station}", end="  " if i % 4 != 0 else "\n")
                        print("\n" + "-" * 40)
                        print("[提示] 直接按回车表示'全部'，不进行该项筛选")
                        try:
                            idx_input = input("输入序号选择（按回车跳过）: ").strip()
                            if idx_input:
                                idx = int(idx_input)
                                if 1 <= idx <= len(all_to_stations):
                                    new_to = all_to_stations[idx - 1]
                                else:
                                    print("\n[!] 序号超出范围")
                                    time.sleep(0.5)
                                    continue
                            else:
                                new_to = None
                        except (ValueError, IndexError):
                            print("\n[!] 无效输入")
                            time.sleep(0.5)
                            continue
                    else:
                        print("\n[提示] 直接按回车表示'全部'，不进行该项筛选")
                        new_to = input("输入精确到达站（按回车键跳过）: ").strip()
                    current_filters['to'] = new_to if new_to else None
                    print(f"\n[✓] 到达站筛选已设置为：{new_to if new_to else '全部'}")
                    time.sleep(0.5)

                # 时段筛选 (6-0)
                elif choice == '6':
                    current_filters['time_period'] = None
                    print("\n[✓] 时段筛选已重置为：全部时段")
                    time.sleep(0.5)
                elif choice == '7':
                    current_filters['time_period'] = 0
                    print("\n[✓] 时段筛选已设置为：00:00-06:00")
                    time.sleep(0.5)
                elif choice == '8':
                    current_filters['time_period'] = 1
                    print("\n[✓] 时段筛选已设置为：06:00-12:00")
                    time.sleep(0.5)
                elif choice == '9':
                    current_filters['time_period'] = 2
                    print("\n[✓] 时段筛选已设置为：12:00-18:00")
                    time.sleep(0.5)
                elif choice == '0':
                    current_filters['time_period'] = 3
                    print("\n[✓] 时段筛选已设置为：18:00-24:00")
                    time.sleep(0.5)

                # 排序选项 (A-F)
                elif choice == 'a':
                    current_filters['sort'] = 'earliest_depart'
                    print("\n[✓] 排序方式已设置为：最早发车")
                    time.sleep(0.5)
                elif choice == 'b':
                    current_filters['sort'] = 'latest_depart'
                    print("\n[✓] 排序方式已设置为：最晚发车")
                    time.sleep(0.5)
                elif choice == 'c':
                    current_filters['sort'] = 'earliest_arrival'
                    print("\n[✓] 排序方式已设置为：最早到达")
                    time.sleep(0.5)
                elif choice == 'd':
                    current_filters['sort'] = 'latest_arrival'
                    print("\n[✓] 排序方式已设置为：最晚到达")
                    time.sleep(0.5)
                elif choice == 'e':
                    current_filters['sort'] = 'shortest'
                    print("\n[✓] 排序方式已设置为：最短历时")
                    time.sleep(0.5)
                elif choice == 'f':
                    current_filters['sort'] = 'longest'
                    print("\n[✓] 排序方式已设置为：最长历时")
                    time.sleep(0.5)

                # 重置筛选
                elif choice == 'r':
                    current_filters['type'] = None
                    current_filters['from'] = None
                    current_filters['to'] = None
                    current_filters['time_period'] = None
                    current_filters['sort'] = None
                    print("\n[✓] 所有筛选条件已重置")
                    time.sleep(0.5)

                # 返回主查询
                elif choice == 'x':
                    return (True, current_filters)

                else:
                    print("\n[!] 无效选择")
                    time.sleep(0.5)

            except KeyboardInterrupt:
                return (True, current_filters)

    def start_query(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 ver 2.0 design by BH7GUL ===")
        print("="*65)

        f_st = input("1. 始发城市/站: ").strip()
        t_st = input("2. 到达城市/站: ").strip()
        date = input("3. 出发日期 (YYYY-MM-DD): ").strip()
        t_in = input("4. 监控车次 (回车全部): ").strip()
        target = t_in.split() if t_in else None

        type_filter, sel_from, sel_to = None, None, None

        # 新增：更新通知管理器的目标车次
        if self.notification_manager:
            self.notification_manager.config.target_trains = target
            if target:
                self.logger.info(f"仅监控目标车次: {target}")
            else:
                self.logger.info("监控所有车次")

        # 新增：记录监控开始
        target_str = ', '.join(target) if target else '全部'
        self.logger.info(f"开始监控: {f_st} -> {t_st}, 日期: {date}, 目标车次: {target_str}")

        # 初始化筛选状态
        filters = {
            'type': None,      # 车型筛选
            'from': None,      # 始发站筛选
            'to': None,        # 到达站筛选
            'time_period': None,  # 时段筛选
            'sort': None       # 排序方式
        }

        while True:
            data = self.query_tickets(date, f_st, t_st)

            # 站名匹配失败处理
            if data == "STATION_NOT_FOUND":
                print(f"\n[!] 错误：无法识别站名。请检查是否输入了简写或错别字。")
                input("请按 [回车键] 重新开始查询...")
                return self.start_query()

            now = datetime.now().strftime("%H:%M:%S")
            os.system('cls' if os.name == 'nt' else 'clear')

            mode_str = "官方定义" if self.config["dc_classification"]["default_mode"] == "official" else "智能识别(动集归普)"
            print(f"[{now}] {f_st} -> {t_st} ({date}) | 模式: {mode_str}")
            print(f"当前筛选: 类型[{filters['type'] or '全部'}] | 始发[{filters['from'] or '全部'}] | 到达[{filters['to'] or '全部'}] | 时段[{filters['time_period'] if filters['time_period'] is None else {0: '00-06', 1: '06-12', 2: '12-18', 3: '18-24'}.get(filters['time_period'])}]")
            print("-" * 110)
            print("[F]筛选排序  [M]切换模式  [E]导出结果  [R]重新查询  [Q]退出")

            if data:
                # 使用筛选参数调用 parse_and_print
                available_tickets = self.parse_and_print(
                    data,
                    target,
                    filters['type'],
                    filters['from'],
                    filters['to'],
                    date,
                    time_period=filters['time_period'],
                    sort_type=filters['sort']
                )

                # 新增：记录查询历史
                train_list = [t.train_no for t in available_tickets]
                self.query_history.record(f_st, t_st, date, len(data), train_list)

                # 新增：发送通知
                if self.notification_manager and available_tickets:
                    # 获取当前监控车次数量（通知前）
                    monitored_before = self.notification_manager.get_monitored_count()

                    self.logger.info(f"发现 {len(available_tickets)} 个有票车次: {train_list}")
                    results = self.notification_manager.notify_ticket_available(available_tickets)

                    # 获取新增的监控车次数量
                    monitored_after = self.notification_manager.get_monitored_count()
                    new_count = monitored_after - monitored_before

                    # 显示监控信息
                    print(f"\n[监控信息] 当前监控 {monitored_after} 个有票车次，本次发现 {len(available_tickets)} 个有票车次")
                    if new_count > 0:
                        print(f"[新发现] {new_count} 个新车次有票！（已发送强提醒）")

                    # 记录通知结果
                    for train_no, channel_results in results.items():
                        self.logger.debug(f"  {train_no} 通知结果: {channel_results}")
            else:
                self.logger.warning("查询返回空数据")
                print("\n目前没有符合条件的列车。")

            wait_sec = 180
            for i in range(wait_sec, 0, -1):
                print(f"\r{i}s 后刷新... (Enter立即刷新)", end="", flush=True)
                if msvcrt.kbhit():
                    key = msvcrt.getch().lower()
                    if key == b'\r':
                        self.logger.debug("用户手动触发刷新")
                        break
                    if key == b'f':
                        # 触发筛选/排序二级菜单
                        should_continue, filters = self.show_filter_menu(filters, data)
                        break
                    if key == b'm':
                        curr = self.config["dc_classification"]["default_mode"]
                        self.config["dc_classification"]["default_mode"] = "smart" if curr == "official" else "official"
                        self.save_config()
                        new_mode = self.config["dc_classification"]["default_mode"]
                        self.logger.info(f"切换DC识别模式: {curr} -> {new_mode}")
                        break
                    if key == b'e' and data:
                        # 导出所有查询结果
                        all_tickets = self.parse_and_print(data, target, filters['type'], filters['from'], filters['to'], date, return_all=True)
                        export_file = os.path.join(self.log_dir, f"tickets_{date}_{datetime.now().strftime('%H%M%S')}.json")
                        self.export_to_json(all_tickets, export_file)
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


if __name__ == "__main__":
    if os.name == 'nt': os.system('')
    app = TrainMonitor()
    try:
        app.show_main_menu()
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0)
