"""
查询缓存服务
减少 12306 API 请求压力，提高响应速度
"""

import time
from typing import List, Optional, Dict, Any, Tuple


class CacheService:
    """查询缓存服务"""

    def __init__(self, ttl_seconds: int = 10):
        """
        初始化缓存服务
        :param ttl_seconds: 缓存生存时间（秒）
        """
        self.ttl_seconds = ttl_seconds
        # key: (from_station, to_station, date)
        # value: (raw_data, expire_time)
        self._cache: Dict[Tuple[str, str, str], Tuple[List[str], float]] = {}

    def _make_key(self, from_station: str, to_station: str, date: str) -> Tuple[str, str, str]:
        """生成缓存键"""
        return (from_station.strip(), to_station.strip(), date.strip())

    def get(self, from_station: str, to_station: str, date: str) -> Optional[List[str]]:
        """
        从缓存获取查询结果
        :param from_station: 始发站
        :param to_station: 到达站
        :param date: 出发日期
        :return: 缓存的查询结果，过期或不存在返回 None
        """
        key = self._make_key(from_station, to_station, date)
        if key in self._cache:
            raw_data, expire_time = self._cache[key]
            if time.time() < expire_time:
                return raw_data
            else:
                # 缓存已过期，删除
                del self._cache[key]
        return None

    def set(self, from_station: str, to_station: str, date: str, raw_data: List[str]) -> None:
        """
        设置缓存
        :param from_station: 始发站
        :param to_station: 到达站
        :param date: 出发日期
        :param raw_data: 查询结果原始数据
        """
        key = self._make_key(from_station, to_station, date)
        expire_time = time.time() + self.ttl_seconds
        self._cache[key] = (raw_data, expire_time)

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()

    def invalidate(self, from_station: str, to_station: str, date: str) -> None:
        """
        使特定查询的缓存失效
        :param from_station: 始发站
        :param to_station: 到达站
        :param date: 出发日期
        """
        key = self._make_key(from_station, to_station, date)
        if key in self._cache:
            del self._cache[key]

    def get_cache_size(self) -> int:
        """获取当前缓存条目数"""
        return len(self._cache)
