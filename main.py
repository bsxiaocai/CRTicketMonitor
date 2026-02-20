import requests
import time
import re
import json
import os
import sys
import msvcrt
from datetime import datetime
from prettytable import PrettyTable

class TrainMonitor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.station_json = os.path.join(base_dir, "station_codes.json")
        self.config_json = os.path.join(base_dir, "config.json")

        self.station_dict = {}
        self.code_to_name = {}
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        }
        
        # 默认使用官方定义
        self.config = {
            "dc_classification": {
                "default_mode": "official",
                "smart_threshold": 899,
                "custom_mapping": {}
            }
        }
        
        self.load_config()
        self.init_station_data()

    def load_config(self):
        if os.path.exists(self.config_json):
            try:
                with open(self.config_json, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except: pass

    def save_config(self):
        try:
            with open(self.config_json, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except: pass

    def init_station_data(self):
        """同步车站编码数据"""
        try:
            url = f'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?v={time.time()}'
            res = self.session.get(url, timeout=10)
            matched = re.findall(r'([\u4e00-\u9fa5]+)\|([A-Z]+)', res.text)
            if matched:
                self.station_dict = {name: code for name, code in matched}
                with open(self.station_json, "w", encoding="utf-8") as f:
                    json.dump(self.station_dict, f, ensure_ascii=False, indent=4)
        except:
            if os.path.exists(self.station_json):
                with open(self.station_json, "r", encoding="utf-8") as f:
                    self.station_dict = json.load(f)
        
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
            self.init_station_data()

        from_code = self.station_dict.get(from_station)
        to_code = self.station_dict.get(to_station)
        
        if not from_code or not to_code:
            return "STATION_NOT_FOUND"

        url = f"https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
        try:
            self.session.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=self.headers, timeout=5)
            response = self.session.get(url, headers=self.headers, timeout=10)
            return response.json().get('data', {}).get('result', [])
        except:
            return None

    def parse_and_print(self, raw_data, target_trains=None, type_filter=None, sel_from=None, sel_to=None):
        table = PrettyTable()
        # 更新表头名称
        table.field_names = ["车次", "始发", "到达", "开点", "到点", "历时", "商/特", "一等座", "二等座", "一等/软卧", "二等/硬卧", "软座", "硬座", "无座"]
        
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
            
            table.add_row(row)
        print(table)

    def start(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*65)
        print("=== 12306 余票查询与监控助手 ver 1.1.0 design by BH7GUL ===")
        print("="*65)
        
        f_st = input("1. 始发城市/站: ").strip()
        t_st = input("2. 到达城市/站: ").strip()
        date = input("3. 出发日期 (YYYY-MM-DD): ").strip()
        t_in = input("4. 监控车次 (回车全部): ").strip()
        target = t_in.split() if t_in else None

        type_filter, sel_from, sel_to = None, None, None

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
            print("[S]筛选车型  [F]筛选站点  [M]切换对动集的识别模式  [C]重置筛选  [R]重新查询  [Q]退出")

            if data:
                self.parse_and_print(data, target, type_filter, sel_from, sel_to)
            else:
                print("\n目前没有符合条件的列车。")

            wait_sec = 180
            for i in range(wait_sec, 0, -1):
                print(f"\r{i}s 后刷新... (Enter立即刷新)", end="", flush=True)
                if msvcrt.kbhit():
                    key = msvcrt.getch().lower()
                    if key == b'\r': break
                    if key == b's':
                        print("\n1.全部  2.高铁动车  3.普通车")
                        opt = input("选择(1/2/3): ").strip()
                        type_filter = {"2": "高铁动车", "3": "普通车"}.get(opt)
                        break
                    if key == b'f' and data:
                        s_from = sorted(list(set(self.code_to_name.get(x.split('|')[6], x.split('|')[6]) for x in data)))
                        s_to = sorted(list(set(self.code_to_name.get(x.split('|')[7], x.split('|')[7]) for x in data)))
                        
                        print("\n" + "-"*30)
                        print(f"[始发站选项]: {s_from}")
                        print(f"[到达站选项]: {s_to}")
                        print("[提示]: 直接按回车表示“全部”，不进行该项筛选") # 增加这一行提示
                        print("-" * 30)

                        sel_from = input("输入精确始发站（按回车键跳过）: ").strip() or None
                        sel_to = input("输入精确到达站（按回车键跳过）: ").strip() or None
                        break
                    if key == b'm':
                        curr = self.config["dc_classification"]["default_mode"]
                        self.config["dc_classification"]["default_mode"] = "smart" if curr == "official" else "official"
                        self.save_config()
                        break
                    if key == b'c':
                        type_filter, sel_from, sel_to = None, None, None
                        break
                    if key == b'r': return self.start()
                    if key == b'q': sys.exit()
                time.sleep(1)

if __name__ == "__main__":
    if os.name == 'nt': os.system('')
    app = TrainMonitor()
    app.start()