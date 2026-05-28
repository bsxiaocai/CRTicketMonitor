"""
导出服务模块
负责将车票数据导出为各种格式
"""

import json
from typing import List, Any, Dict
from datetime import datetime


class ExportService:
    """导出服务"""

    @staticmethod
    def _to_export_dict(item: Any) -> Dict:
        """将车票对象或表格行字典转换为可导出的字典"""
        if isinstance(item, dict):
            return item
        if hasattr(item, "to_dict"):
            return item.to_dict()
        raise TypeError(f"不支持的导出数据类型: {type(item).__name__}")

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
            "tickets": [ExportService._to_export_dict(ticket) for ticket in tickets]
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

        rows = [ExportService._to_export_dict(ticket) for ticket in tickets]

        headers = []
        for row in rows:
            for key in row.keys():
                if key not in headers:
                    headers.append(key)

        with open(filepath, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
