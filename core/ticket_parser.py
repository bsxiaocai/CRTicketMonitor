"""
车票数据解析模块
负责解析和展示车票信息
"""

from prettytable import PrettyTable
from typing import List, Tuple, Dict
import sys


class TicketParser:
    """车票解析器"""

    @staticmethod
    def parse_and_print(raw_data: List[str], ticket_info_list: List, target_trains: List[str] = None,
                       type_filter: str = None, sel_from: str = None, sel_to: str = None,
                       date: str = None, return_all: bool = False,
                       time_period: int = None, sort_type: str = None,
                       station_dict: dict = None, code_to_name: dict = None,
                       classify_func=None, return_table: bool = False) -> List:
        """
        解析并打印车票信息
        :param raw_data: 原始数据列表
        :param ticket_info_list: TicketInfo 列表（用于导出）
        :param target_trains: 目标车次列表
        :param type_filter: 车型筛选
        :param sel_from: 始发站筛选
        :param sel_to: 到达站筛选
        :param date: 出发日期
        :param return_all: 是否返回所有车票
        :param time_period: 时段筛选
        :param sort_type: 排序类型
        :param station_dict: 车站字典
        :param code_to_name: 代码到名称映射
        :param classify_func: 车次分类函数
        :param return_table: 是否返回表格字符串（而非直接打印）
        :return: 车票列表，如果 return_table=True 则返回 (table_str, tickets)
        """
        table = PrettyTable()
        table.field_names = ["车次", "始发", "到达", "开点", "到点", "历时", "商务座/特等座", "一等座", "二等座",
                            "软卧/动卧/一等卧", "硬卧/二等卧", "软座", "硬座", "无座"]

        available_tickets = []
        all_tickets = []
        temp_all = []

        for item in raw_data:
            d = item.split('|')
            train_no = d[3]
            train_type = classify_func(train_no) if classify_func else "其他"

            if type_filter and type_filter not in train_type:
                continue
            if target_trains and train_no not in target_trains:
                continue

            f_st_name = code_to_name.get(d[6], d[6]) if code_to_name else d[6]
            t_st_name = code_to_name.get(d[7], d[7]) if code_to_name else d[7]
            if sel_from and f_st_name != sel_from:
                continue
            if sel_to and t_st_name != sel_to:
                continue

            # 时段筛选
            from .time_filter import TimeFilter
            if not TimeFilter.filter_by_time_period(d[8], time_period):
                continue

            # 坐席解析
            sw = d[32] or "--"
            yd = d[31] or "--"
            ed = d[30] or "--"
            y_wo = d[23] or "--"
            e_wo = d[28] or "--"
            rz = d[24] or "--"
            yz = d[29] or "--"
            wz = d[26] or "--"

            row = [train_no, f_st_name, t_st_name, d[8], d[9], d[10], sw, yd, ed, y_wo, e_wo, rz, yz, wz]

            # 坐席信息
            seats = {'商/特': sw, '一等座': yd, '二等座': ed,
                    '一等/软卧': y_wo, '二等/硬卧': e_wo, '软座': rz, '硬座': yz, '无座': wz}

            # S 字头特殊逻辑：当只有二等座、无座两种席位时，任一有票即认定为有票
            if train_no.upper().startswith('S'):
                # 检查是否只有二等座和无座席位（其他席位都是"--"）
                only_ed_wz = (sw == "--" and yd == "--" and y_wo == "--" and e_wo == "--" and rz == "--" and yz == "--")

                if only_ed_wz:
                    # 只有二等座和无座时，任一有票即认定为有票
                    ed_has = ed not in ['无', '--', '', '0']
                    wz_has = wz not in ['无', '--', '', '0']
                    has_ticket = ed_has or wz_has
                else:
                    # 有其他席位时，使用基础逻辑
                    has_ticket = any(s not in ['无', '--', '', '0'] for s in [sw, yd, ed, y_wo, e_wo, rz, yz, wz])
            else:
                # 基础着色逻辑（非 S 字头：有任意票即绿）
                has_ticket = any(s not in ['无', '--', '', '0'] for s in [sw, yd, ed, y_wo, e_wo, rz, yz])

            # 着色处理
            if train_no.upper().startswith('S'):
                if has_ticket:
                    row[0] = f"\033[92m{train_no}\033[0m"
            else:
                if has_ticket:
                    row[0] = f"\033[92m{train_no}\033[0m"

            # 为所有车次创建 TicketInfo（用于导出）
            from notification.base import TicketInfo
            available_seats = {k: v for k, v in seats.items() if v not in ['无', '--', '', '0']}
            if date:
                ticket_info = TicketInfo(
                    train_no=train_no,
                    from_station=f_st_name,
                    to_station=t_st_name,
                    date=date,
                    departure_time=d[8],
                    arrival_time=d[9],
                    duration=d[10],
                    available_seats=available_seats if has_ticket else {}
                )
                all_tickets.append(ticket_info)

                if has_ticket:
                    available_tickets.append(ticket_info)

            temp_all.append((ticket_info, d, row))

        # 排序
        if sort_type:
            temp_all = TicketParser.sort_tickets(temp_all, sort_type)

        # 添加到表格
        for _, _, row in temp_all:
            table.add_row(row)

        if return_table:
            # 返回表格字符串和车票列表
            return str(table), all_tickets if return_all else available_tickets
        else:
            # 直接打印
            print(table)
            return all_tickets if return_all else available_tickets

    @staticmethod
    def sort_tickets(tickets_with_data: List[Tuple], sort_type: str) -> List[Tuple]:
        """
        排序功能
        :param tickets_with_data: [(TicketInfo, raw_data), ...]
        :param sort_type: 排序类型
        :return: 排序后的列表
        """
        def time_to_minutes(t: str) -> int:
            """将 HH:MM 格式转换为分钟数"""
            try:
                h, m = map(int, t.split(':'))
                return h * 60 + m
            except Exception:
                return 99999

        def duration_to_minutes(d: str) -> int:
            """将历时转换为分钟数"""
            try:
                h, m = map(int, d.split(':'))
                return h * 60 + m
            except Exception:
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
        return tickets_with_data

    @staticmethod
    def extract_seat_info(raw_data_item: str) -> Dict[str, str]:
        """
        提取坐席信息
        :param raw_data_item: 原始数据项
        :return: 坐席信息字典
        """
        d = raw_data_item.split('|')
        return {
            '商务/特等': d[32] or "--",
            '一等座': d[31] or "--",
            '二等座': d[30] or "--",
            '一等/软卧': d[23] or "--",
            '二等/硬卧': d[28] or "--",
            '软座': d[24] or "--",
            '硬座': d[29] or "--",
            '无座': d[26] or "--"
        }
