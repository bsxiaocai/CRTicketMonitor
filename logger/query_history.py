"""
查询历史记录管理
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional


class QueryHistory:
    """查询历史记录管理器"""

    def __init__(self, log_dir: str):
        """
        初始化查询历史记录器
        :param log_dir: 日志目录路径
        """
        self.log_dir = log_dir
        self.history_file = os.path.join(log_dir, "query_history.jsonl")

    def record(self, from_station: str, to_station: str, date: str,
               total_count: int, available_trains: List[str]):
        """
        记录一次查询
        :param from_station: 始发站
        :param to_station: 到达站
        :param date: 出发日期
        :param total_count: 返回的总记录数
        :param available_trains: 有票的车次列表
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "from": from_station,
            "to": to_station,
            "date": date,
            "total_count": total_count,
            "available_count": len(available_trains),
            "available_trains": available_trains
        }

        try:
            with open(self.history_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_recent(self, limit: int = 100) -> List[Dict]:
        """
        获取最近的查询历史
        :param limit: 获取数量限制
        :return: 查询记录列表
        """
        records = []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        except FileNotFoundError:
            return []

        return records[-limit:]

    def get_statistics(self) -> Dict:
        """
        获取查询统计信息
        :return: 统计字典
        """
        records = self.get_recent(1000)
        if not records:
            return {}

        # 统计各车次的有票次数
        train_counts = {}
        for r in records:
            for train in r['available_trains']:
                train_counts[train] = train_counts.get(train, 0) + 1

        return {
            "total_queries": len(records),
            "total_with_tickets": sum(1 for r in records if r['available_count'] > 0),
            "top_trains": sorted(train_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
