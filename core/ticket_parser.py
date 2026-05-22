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
    def _safe_get(data_list: list, index: int, default: str = "--") -> str:
        """
        安全地从列表中获取指定索引的值
        :param data_list: 数据列表
        :param index: 索引
        :param default: 默认值
        :return: 索引处的值，如果索引越界或值为空则返回默认值
        """
        try:
            if index < len(data_list):
                value = data_list[index]
                return value if value else default
            return default
        except (IndexError, TypeError):
            return default

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
            train_no = TicketParser._safe_get(d, 3, "")
            if not train_no:
                continue
            train_type = classify_func(train_no) if classify_func else "其他"

            if type_filter and type_filter not in train_type:
                continue
            if target_trains and train_no not in target_trains:
                continue

            f_st_code = TicketParser._safe_get(d, 6, "")
            t_st_code = TicketParser._safe_get(d, 7, "")
            f_st_name = code_to_name.get(f_st_code, f_st_code) if code_to_name and f_st_code else f_st_code
            t_st_name = code_to_name.get(t_st_code, t_st_code) if code_to_name and t_st_code else t_st_code
            if sel_from and f_st_name != sel_from:
                continue
            if sel_to and t_st_name != sel_to:
                continue

            # 时段筛选
            departure_time = TicketParser._safe_get(d, 8, "")
            from .time_filter import TimeFilter
            if not TimeFilter.filter_by_time_period(departure_time, time_period):
                continue

            # 坐席解析
            sw = TicketParser._safe_get(d, 32)
            yd = TicketParser._safe_get(d, 31)
            ed = TicketParser._safe_get(d, 30)
            y_wo = TicketParser._safe_get(d, 23)
            e_wo = TicketParser._safe_get(d, 28)
            rz = TicketParser._safe_get(d, 24)
            yz = TicketParser._safe_get(d, 29)
            wz = TicketParser._safe_get(d, 26)

            row = [train_no, f_st_name, t_st_name, departure_time,
                   TicketParser._safe_get(d, 9, ""), TicketParser._safe_get(d, 10, ""),
                   sw, yd, ed, y_wo, e_wo, rz, yz, wz]

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
                    departure_time=departure_time,
                    arrival_time=TicketParser._safe_get(d, 9, ""),
                    duration=TicketParser._safe_get(d, 10, ""),
                    available_seats=available_seats if has_ticket else {},
                    internal_train_no=TicketParser._safe_get(d, 2, ""),
                    from_station_no=TicketParser._safe_get(d, 16, ""),
                    to_station_no=TicketParser._safe_get(d, 17, ""),
                    seat_types_code=TicketParser._safe_get(d, 35, ""),
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
            def adjusted_arrival(x):
                depart = time_to_minutes(x[1][8])
                arrival = time_to_minutes(x[1][9])
                dur = duration_to_minutes(x[1][10])
                if arrival < depart and dur > 0:
                    arrival += 24 * 60
                return arrival
            return sorted(tickets_with_data, key=adjusted_arrival)
        elif sort_type == 'latest_arrival':
            def adjusted_arrival_rev(x):
                depart = time_to_minutes(x[1][8])
                arrival = time_to_minutes(x[1][9])
                dur = duration_to_minutes(x[1][10])
                if arrival < depart and dur > 0:
                    arrival += 24 * 60
                return arrival
            return sorted(tickets_with_data, key=adjusted_arrival_rev, reverse=True)
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
            '商务/特等': TicketParser._safe_get(d, 32),
            '一等座': TicketParser._safe_get(d, 31),
            '二等座': TicketParser._safe_get(d, 30),
            '一等/软卧': TicketParser._safe_get(d, 23),
            '二等/硬卧': TicketParser._safe_get(d, 28),
            '软座': TicketParser._safe_get(d, 24),
            '硬座': TicketParser._safe_get(d, 29),
            '无座': TicketParser._safe_get(d, 26)
        }

    @staticmethod
    def parse_transfer_data(raw_data: list, station_dict: dict = None,
                            code_to_name: dict = None, date: str = None) -> list:
        """
        解析中转换乘查询结果
        :param raw_data: 中转 API 返回的 result 列表（每项为 pipe-delimited 字符串）
        :param station_dict: 车站字典 {站名: 代码}
        :param code_to_name: 代码到站名映射 {代码: 站名}
        :param date: 出发日期
        :return: TransferTicketInfo 列表
        """
        from notification.base import TicketInfo, TransferTicketInfo

        transfers = []
        for item in raw_data:
            d = item.split('|')
            try:
                # 中转 API 响应格式：每条记录包含两程列车信息
                # 第一程：标准索引 d[3]=车次, d[6]=出发站代码, d[7]=到达站代码(中转站), d[8]=出发时间, d[9]=到达时间, d[10]=历时
                # 第二程：偏移索引，具体位置需实际验证，以下为推测值
                # 中转响应中 d[0] 通常为第一程的 secretStr

                # 第一程
                first_train_no = TicketParser._safe_get(d, 3, "")
                if not first_train_no:
                    continue
                first_from_code = TicketParser._safe_get(d, 6, "")
                first_to_code = TicketParser._safe_get(d, 7, "")  # 中转站代码
                first_from = code_to_name.get(first_from_code, first_from_code) if code_to_name and first_from_code else first_from_code
                transfer_station = code_to_name.get(first_to_code, first_to_code) if code_to_name and first_to_code else first_to_code

                first_leg = TicketInfo(
                    train_no=first_train_no,
                    from_station=first_from,
                    to_station=transfer_station,
                    date=date or "",
                    departure_time=TicketParser._safe_get(d, 8, ""),
                    arrival_time=TicketParser._safe_get(d, 9, ""),
                    duration=TicketParser._safe_get(d, 10, ""),
                    available_seats={},
                    internal_train_no=TicketParser._safe_get(d, 2, ""),
                    from_station_no=TicketParser._safe_get(d, 16, ""),
                    to_station_no=TicketParser._safe_get(d, 17, ""),
                    seat_types_code=TicketParser._safe_get(d, 35, ""),
                )

                # 第二程 - 中转 API 中第二程信息在记录的后半部分
                # 索引偏移量约为 33（需实际验证）
                second_train_no = TicketParser._safe_get(d, 33, "")
                second_from = transfer_station  # 第二程出发站 = 中转站
                second_to_code = TicketParser._safe_get(d, 37, "")
                second_to = code_to_name.get(second_to_code, second_to_code) if code_to_name and second_to_code else second_to_code

                second_leg = TicketInfo(
                    train_no=second_train_no,
                    from_station=second_from,
                    to_station=second_to,
                    date=date or "",
                    departure_time=TicketParser._safe_get(d, 34, ""),
                    arrival_time=TicketParser._safe_get(d, 35, ""),
                    duration=TicketParser._safe_get(d, 36, ""),
                    available_seats={},
                )

                # 计算中转等待时间
                wait_time = ""
                if first_leg.arrival_time and second_leg.departure_time:
                    try:
                        arr_h, arr_m = map(int, first_leg.arrival_time.split(':'))
                        dep_h, dep_m = map(int, second_leg.departure_time.split(':'))
                        wait_minutes = (dep_h * 60 + dep_m) - (arr_h * 60 + arr_m)
                        if wait_minutes < 0:
                            wait_minutes += 24 * 60  # 跨天修正
                        wait_time = f"{wait_minutes // 60}小时{wait_minutes % 60}分"
                    except (ValueError, AttributeError):
                        pass

                # 计算总历时
                total_duration = ""
                if first_leg.departure_time and second_leg.arrival_time:
                    try:
                        dep_h, dep_m = map(int, first_leg.departure_time.split(':'))
                        arr_h, arr_m = map(int, second_leg.arrival_time.split(':'))
                        total_minutes = (arr_h * 60 + arr_m) - (dep_h * 60 + dep_m)
                        if total_minutes < 0:
                            total_minutes += 24 * 60
                        total_duration = f"{total_minutes // 60}:{total_minutes % 60:02d}"
                    except (ValueError, AttributeError):
                        pass

                transfer = TransferTicketInfo(
                    first_leg=first_leg,
                    second_leg=second_leg,
                    transfer_station=transfer_station,
                    total_duration=total_duration,
                    wait_time=wait_time,
                )
                transfers.append(transfer)

            except (IndexError, ValueError) as e:
                # 跳过格式异常的记录
                continue

        return transfers
