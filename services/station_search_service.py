"""
车站搜索服务
支持拼音首字母自动补全，集成 pypinyin 实现全量动态拼音转换
"""

from typing import List, Dict
from pypinyin import lazy_pinyin, Style


class StationSearchService:
    """车站搜索服务"""

    def __init__(self, station_dict: Dict[str, str]):
        """
        初始化车站搜索服务
        :param station_dict: 车站字典 {站名：代码}
        """
        self.station_dict = station_dict
        self.station_names = list(station_dict.keys())
        # 动态构建全量拼音索引
        self._pinyin_cache: Dict[str, List[str]] = {}  # station -> [pinyin_initials, full_pinyin]
        self._letter_map: Dict[str, List[str]] = {}     # letter_pattern -> [stations]
        self._build_pinyin_index()

    def _build_pinyin_index(self):
        """构建全量拼音索引"""
        for station in self.station_names:
            initials, full = self._get_pinyin(station)
            self._pinyin_cache[station] = [initials, full]

            # 将首字母和全拼加入倒排索引
            for key in [initials, full]:
                if key and key not in self._letter_map:
                    self._letter_map[key] = []
                if key and station not in self._letter_map[key]:
                    self._letter_map[key].append(station)

    def _get_pinyin(self, station_name: str) -> tuple:
        """
        获取车站名称的拼音首字母和全拼
        :param station_name: 站名
        :return: (首字母, 全拼)
        """
        try:
            # 拼音首字母（如 "长沙南" -> "csn"）
            initials = ''.join(
                lazy_pinyin(station_name, style=Style.FIRST_LETTER)
            ).lower()

            # 全拼（如 "长沙南" -> "changshanan"）
            full = ''.join(lazy_pinyin(station_name)).lower()

            return initials, full
        except Exception:
            return '', station_name

    def search_station(self, keyword: str) -> List[str]:
        """
        搜索车站
        :param keyword: 搜索关键词（支持站名、拼音首字母、全拼）
        :return: 匹配的车站站名列表
        """
        if not keyword:
            return []

        keyword_lower = keyword.lower().strip()
        results = set()

        # 1. 精确匹配站名
        if keyword in self.station_dict:
            results.add(keyword)

        # 2. 模糊匹配站名（包含关键词）
        for station in self.station_names:
            if keyword in station:
                results.add(station)

        # 3. 精确匹配拼音首字母或全拼
        if keyword_lower in self._letter_map:
            for station in self._letter_map[keyword_lower]:
                if station in self.station_dict:
                    results.add(station)

        # 4. 前缀匹配拼音（如输入 "cs" 匹配 "csn", "csha" 等）
        for key, stations in self._letter_map.items():
            if key.startswith(keyword_lower):
                for station in stations:
                    if station in self.station_dict:
                        results.add(station)

        # 5. 子串匹配拼音（如输入 "sha" 匹配 "changsha"）
        if len(keyword_lower) >= 2:
            for key, stations in self._letter_map.items():
                if keyword_lower in key:
                    for station in stations:
                        if station in self.station_dict:
                            results.add(station)

        # 限制返回数量
        return sorted(list(results))[:20]

    def get_station_code(self, station_name: str) -> str:
        """
        获取车站代码
        :param station_name: 站名
        :return: 车站代码，找不到返回空字符串
        """
        return self.station_dict.get(station_name, "")

    def get_stations_by_city(self, city_name: str) -> List[str]:
        """
        根据城市名获取该城市的所有车站
        :param city_name: 城市名（如"长沙"、"北京"）
        :return: 该城市的所有车站列表
        """
        if not city_name:
            return []

        results = []
        # 匹配包含城市名的车站（如"长沙"匹配"长沙"、"长沙南"、"长沙西"）
        for station in self.station_names:
            if station.startswith(city_name):
                results.append(station)

        # 如果没有找到，尝试模糊匹配
        if not results:
            for station in self.station_names:
                if city_name in station:
                    results.append(station)

        # 如果仍然没有，尝试拼音匹配
        if not results:
            city_lower = city_name.lower()
            for station, (initials, full) in self._pinyin_cache.items():
                if initials.startswith(city_lower) or full.startswith(city_lower):
                    results.append(station)

        return sorted(list(set(results)))
