"""
数据展示模块
负责格式化显示车票信息
"""

from prettytable import PrettyTable
from typing import List, Dict


class Display:
    """数据展示器"""

    @staticmethod
    def print_statistics(stats: Dict) -> None:
        """
        打印统计信息
        :param stats: 统计数据字典
        """
        print(f"\n【查询统计】")
        print(f"  总查询次数: {stats.get('total_queries', 0)}")
        print(f"  有票查询次数: {stats.get('total_with_tickets', 0)}")
        total = stats.get('total_queries', 0)
        with_tickets = stats.get('total_with_tickets', 0)
        if total > 0:
            print(f"  有票率: {with_tickets/total*100:.1f}%")

    @staticmethod
    def print_query_history(records: List[Dict], limit: int = 50) -> None:
        """
        打印查询历史
        :param records: 查询记录列表
        :param limit: 显示数量限制
        """
        print(f"\n【最近查询记录】")
        print("-" * 70)
        for i, rec in enumerate(reversed(records[:limit]), 1):
            timestamp = rec['timestamp'].split('T')[1][:8] if 'T' in rec['timestamp'] else rec['timestamp']
            has_ticket = "✓" if rec['available_count'] > 0 else "✗"
            trains = ", ".join(rec['available_trains'][:3]) if rec['available_trains'] else "无"
            print(f"{i:2d}. [{timestamp}] {rec['from']:4s} -> {rec['to']:4s} ({rec['date']}) {has_ticket} {rec['available_count']:2d}车次 {trains}")

    @staticmethod
    def print_notification_channels(channels: List[str]) -> None:
        """
        打印可用的通知渠道
        :param channels: 通知渠道名称列表
        """
        if channels:
            print(f"可用通知渠道: {', '.join(channels)}")
        else:
            print("暂无可用通知渠道")
