import requests
import time
import random
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
        self.json_file = os.path.join(base_dir, "station_codes.json")
        
        self.station_dict = {}
        self.code_to_name = {}
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://kyfw.12306.cn/otn/leftTicket/init",
        }
        # 初始化时进行第一次同步
        self.init_station_data()

    def init_station_data(self):
        """同步车站数据并建立双向映射"""
        local_count = 0
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, "r", encoding="utf-8") as f:
                    self.station_dict = json.load(f)
                    local_count = len(self.station_dict)
            except: pass
        
        print(f"[*] 正在从12306同步车站数据 (本地已有: {local_count})...")
        try:
            # 增加随机参数绕过缓存
            res = self.session.get(f'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?v={time.time()}', timeout=10)
            matched = re.findall(r'([\u4e00-\u9fa5]+)\|([A-Z]+)', res.text)
            if matched:
                remote_data = {name: code for name, code in matched}
                before_count = len(self.station_dict)
                self.station_dict.update(remote_data)
                after_count = len(self.station_dict)
                
                with open(self.json_file, "w", encoding="utf-8") as f:
                    json.dump(self.station_dict, f, ensure_ascii=False, indent=4)
                
                print(f"[√] 数据同步成功！本次新增: {after_count - before_count} 个，当前总计: {after_count} 个站点。")
            else:
                print("[!] 解析失败，请检查12306接口是否变动。")
        except Exception as e:
            print(f"[!] 同步失败: {e}。将尝试使用现有本地数据。")
        
        # 建立代码到站名的反向映射
        self.code_to_name = {code: name for name, code in self.station_dict.items()}

    def query_tickets(self, date, from_station, to_station):
        """执行查询，若车站不存在则触发一次自动同步"""
        if from_station not in self.station_dict or to_station not in self.station_dict:
            print(f"\n[?] 发现未知车站或城市，正在尝试第二次在线同步...")
            self.init_station_data()

        from_code = self.station_dict.get(from_station)
        to_code = self.station_dict.get(to_station)
        
        if not from_code or not to_code:
            missing = from_station if not from_code else to_station
            print(f"\n[!] 错误：找不到车站或该城市 '{missing}'。请确保输入的是标准站名。")
            return "STATION_NOT_FOUND"

        url = f"https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
        try:
            self.session.get("https://kyfw.12306.cn/otn/leftTicket/init", headers=self.headers)
            response = self.session.get(url, headers=self.headers, timeout=10)
            return response.json()['data']['result']
        except Exception as e:
            return None

    def parse_and_print(self, raw_data, target_trains=None):
        """解析并展示常用坐席"""
        table = PrettyTable()
        # 更新表头，加入“软座”
        table.field_names = ["车次", "始发", "到达", "开点", "到点", "历时", "商务", "一等座", "二等座", "软/一等卧", "硬/二等卧", "硬座", "软座", "无座"]
        
        for item in raw_data:
            d = item.split('|')
            train_no = d[3]
            if target_trains and train_no not in target_trains: continue

            from_nm = self.code_to_name.get(d[6], d[6])
            to_nm = self.code_to_name.get(d[7], d[7])

            # 提取票额信息
            sw = d[32] or "--"   # 商务/特等
            yd = d[31] or "--"   # 一等座
            ed = d[30] or "--"   # 二等座
            rz = d[24] or "--"   # 软座 (索引 24)
            y_wo = d[23] or "--" # 一等卧/软卧
            e_wo = d[28] or "--" # 二等卧/硬卧
            yz = d[29] or "--"   # 硬座
            wz = d[26] or "--"   # 无座

            # 变绿逻辑：常用坐席（含软座）中有票
            major_seats = [sw, yd, ed, rz, y_wo, e_wo, yz]
            has_ticket = any(s not in ['无', '--', '', '0'] for s in major_seats)

            # 构造行数据
            row = [train_no, from_nm, to_nm, d[8], d[9], d[10], sw, yd, ed, y_wo, e_wo, yz, rz, wz]

            if has_ticket:
                row[0] = f"\033[92m{train_no}\033[0m" # 有票时车次显示绿色

            table.add_row(row)
        
        print(table)

    def start(self):
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n" + "="*65)
            print("=== 12306 余票查询与监控助手 ver 1.0.1 design by BH7GUL ===")
            print("="*65)
            print(" [操作提示]: 输入 Q 退出程序 | 请输入正确的出发和到达的城市")
            print("-" * 65)
            
            f_st = input("1. 始发站: ").strip()
            if f_st.upper() == 'Q': break
            t_st = input("2. 到达站: ").strip()
            if t_st.upper() == 'Q': break
            
            date = input("3. 出发日期 (如 2026-01-01): ").strip()
            if date.upper() == 'Q': break
            
            t_input = input("4. 监控特定车次 (空格分隔，直接回车监控全部): ").strip()
            if t_input.upper() == 'Q': break
            target = t_input.split() if t_input else None
            
            mode = '1' # 1:自动, 2:手动
            print("\n[OK] 监控已就绪。正在进入实时界面...")
            time.sleep(1)

            while True:
                now = datetime.now().strftime("%H:%M:%S")
                data = self.query_tickets(date, f_st, t_st)
                
                if data == "STATION_NOT_FOUND":
                    input("\n[!] 车站匹配失败，按回车返回重新输入..."); break

                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"路线: {f_st} -> {t_st} | 日期: {date} | 模式: {'[自动刷新]' if mode=='1' else '[手动触发]'}")
                print(f"时间: {now} | 指令: [R]新查询 | [Q]退出 | [M/A]切模式 | [Enter]刷新")
                print("-" * 125)

                if data:
                    self.parse_and_print(data, target)
                else:
                    print("[!] 接口获取失败。可能频率过快或网络波动。")

                action = None
                if mode == '1':
                    wait_time = 180 + random.randint(1, 5)
                    for i in range(wait_time, 0, -1):
                        print(f"\r倒计时 {i}s 后刷新 | [R]返回 [Q]退出 [M]转手动 [Enter]立即刷新  ", end="", flush=True)
                        if msvcrt.kbhit():
                            key = msvcrt.getch().lower()
                            if key == b'\r': break
                            if key == b'q': action = 'quit'; break
                            if key == b'r': action = 'reset'; break
                            if key == b'm': mode = '2'; break
                        time.sleep(1)
                else:
                    print("\n[手动模式] 按 [Enter] 刷新 | [A] 转自动 | [R] 返回 | [Q] 退出")
                    while True:
                        if msvcrt.kbhit():
                            key = msvcrt.getch().lower()
                            if key == b'\r': break
                            if key == b'q': action = 'quit'; break
                            if key == b'r': action = 'reset'; break
                            if key == b'a': mode = '1'; break
                        time.sleep(0.1)

                if action == 'quit': sys.exit()
                if action == 'reset': break

if __name__ == "__main__":
    import os
    os.system("title 12306余票查询与监控助手 v1.0.1 BY BH7GUL")
    app = TrainMonitor()
    app.start()