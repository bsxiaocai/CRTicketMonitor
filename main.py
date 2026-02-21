import requests
import time
import re
import json
import os
import sys
import msvcrt
import atexit
from datetime import datetime
from prettytable import PrettyTable

# 新增：导入日志和通知模块
from logger import TicketLogger, QueryHistory
from notification import NotificationManager, NativeWindowsNotification, TicketInfo


class TrainMonitor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.station_json = os.path.join(base_dir, "station_codes.json")
        self.config_json = os.path.join(base_dir, "config.json")
        self.log_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)

        # 新增：初始化日志
        self.logger = TicketLogger(self.log_dir, {})
        self.logger.log_startup("1.2.1")

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

    def parse_and_print(self, raw_data, target_trains=None, type_filter=None, sel_from=None, sel_to=None, date=None, return_all=False):
        """
        解析并打印车票信息
        :param return_all: 是否返回所有车票（包括无票的）
        :return: 有票的车次列表；如果 return_all=True，返回所有车票
        """
        table = PrettyTable()
        table.field_names = ["车次", "始发", "到达", "开点", "到点", "历时", "商/特", "一等座", "二等座", "一等/软卧", "二等/硬卧", "软座", "硬座", "无座"]

        available_tickets = []  # 记录有票的车次
        all_tickets = []  # 记录所有车票

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

            table.add_row(row)
        print(table)
        return all_tickets if return_all else available_tickets  # 根据参数返回

    def start(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 ver 1.2.1 design by BH7GUL ===")
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

        while True:
            data = self.query_tickets(date, f_st, t_st)

            # 站名匹配失败处理
            if data == "STATION_NOT_FOUND":
                print(f"\n[!] 错误：无法识别站名。请检查是否输入了简写或错别字。")
                input("请按 [回车键] 重新开始查询...")
                return self.start()

            now = datetime.now().strftime("%H:%M:%S")
            os.system('cls' if os.name == 'nt' else 'clear')

            mode_str = "官方定义" if self.config["dc_classification"]["default_mode"] == "official" else "智能识别(动集归普)"
            print(f"[{now}] {f_st} -> {t_st} ({date}) | 模式: {mode_str}")
            print(f"当前筛选: 类型[{type_filter or '全部'}] | 始发[{sel_from or '全部'}] | 到达[{sel_to or '全部'}]")
            print("-" * 110)
            print("[S]筛选车型  [F]筛选站点  [M]切换模式  [E]导出结果  [C]重置筛选  [R]重新查询  [Q]退出")

            if data:
                # 新增：获取有票列表并传入日期
                available_tickets = self.parse_and_print(data, target, type_filter, sel_from, sel_to, date)

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
                    if key == b's':
                        print("\n1.全部  2.高铁动车  3.普通车")
                        opt = input("选择(1/2/3): ").strip()
                        type_filter = {"2": "高铁动车", "3": "普通车"}.get(opt)
                        if type_filter:
                            self.logger.debug(f"筛选车型: {type_filter}")
                        break
                    if key == b'f' and data:
                        s_from = sorted(list(set(self.code_to_name.get(x.split('|')[6], x.split('|')[6]) for x in data)))
                        s_to = sorted(list(set(self.code_to_name.get(x.split('|')[7], x.split('|')[7]) for x in data)))

                        print("\n" + "-"*30)
                        print(f"[始发站选项]: {s_from}")
                        print(f"[到达站选项]: {s_to}")
                        print('[提示]: 直接按回车表示"全部"，不进行该项筛选')
                        print("-" * 30)

                        sel_from = input("输入精确始发站（按回车键跳过）: ").strip() or None
                        sel_to = input("输入精确到达站（按回车键跳过）: ").strip() or None
                        self.logger.debug(f"筛选站点: 始发[{sel_from or '全部'}] 到达[{sel_to or '全部'}]")
                        break
                    if key == b'm':
                        curr = self.config["dc_classification"]["default_mode"]
                        self.config["dc_classification"]["default_mode"] = "smart" if curr == "official" else "official"
                        self.save_config()
                        new_mode = self.config["dc_classification"]["default_mode"]
                        self.logger.info(f"切换DC识别模式: {curr} -> {new_mode}")
                        break
                    if key == b'c':
                        type_filter, sel_from, sel_to = None, None, None
                        self.logger.debug("重置所有筛选条件")
                        break
                    if key == b'e' and data:
                        # 导出所有查询结果
                        all_tickets = self.parse_and_print(data, target, type_filter, sel_from, sel_to, date, return_all=True)
                        export_file = os.path.join(self.log_dir, f"tickets_{date}_{datetime.now().strftime('%H%M%S')}.json")
                        self.export_to_json(all_tickets, export_file)
                        print(f"\n[✓] 结果已导出到: {export_file}")
                        input("按回车键继续...")
                        break
                    if key == b'r':
                        self.logger.info("用户重新开始查询")
                        return self.start()
                    if key == b'q':
                        self.logger.info("用户退出程序")
                        sys.exit()
                time.sleep(1)


if __name__ == "__main__":
    if os.name == 'nt': os.system('')
    app = TrainMonitor()
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0)
