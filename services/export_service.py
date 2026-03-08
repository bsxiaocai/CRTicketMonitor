"""
导出服务模块
负责将车票数据导出为各种格式
"""

import json
from typing import List
from datetime import datetime


class ExportService:
    """导出服务"""

    @staticmethod
    def export_to_json(tickets: List, filepath: str) -> None:
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

    @staticmethod
    def export_to_csv(tickets: List, filepath: str) -> None:
        """
        导出车票信息到 CSV 文件（可选功能）
        :param tickets: 车票列表
        :param filepath: 输出文件路径
        """
        import csv
        if not tickets:
            return

        # 获取所有可能的坐席类型
        all_seat_types = set()
        for ticket in tickets:
            all_seat_types.update(ticket.available_seats.keys())

        headers = ["车次", "始发站", "到达站", "日期", "开车时间", "历时"] + list(all_seat_types)

        with open(filepath, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for ticket in tickets:
                row = [
                    ticket.train_no,
                    ticket.from_station,
                    ticket.to_station,
                    ticket.date,
                    ticket.departure_time,
                    ticket.duration
                ]
                for seat_type in all_seat_types:
                    row.append(ticket.available_seats.get(seat_type, "--"))
                writer.writerow(row)
