"""
车站搜索服务
支持拼音首字母自动补全
"""

from typing import List, Dict


class StationSearchService:
    """车站搜索服务"""

    def __init__(self, station_dict: Dict[str, str]):
        """
        初始化车站搜索服务
        :param station_dict: 车站字典 {站名：代码}
        """
        self.station_dict = station_dict
        self.station_names = list(station_dict.keys())
        # 构建首字母映射（简化版：仅支持中文站名的拼音首字母）
        # 由于不依赖 pypinyin，使用常见车站的预映射
        self.first_letter_map = self._build_first_letter_map()

    def _build_first_letter_map(self) -> Dict[str, List[str]]:
        """
        构建首字母到站名的映射
        预置常见城市的拼音首字母
        """
        # 常见车站首字母映射（手动维护常见城市）
        common_stations = {
            'bj': ['北京', '北京北', '北京东', '北京南', '北京西', '北京大兴', '北京朝阳', '北京通州'],
            'sh': ['上海', '上海南', '上海虹桥', '上海西'],
            'gz': ['广州', '广州北', '广州南', '广州东'],
            'sz': ['深圳', '深圳北', '深圳东', '深圳西', '深圳坪山'],
            'cs': ['长沙', '长沙南', '长沙西'],
            'wh': ['武汉', '武汉东', '武汉西', '武汉北'],
            'cd': ['成都', '成都东', '成都南', '成都西'],
            'cq': ['重庆', '重庆北', '重庆西', '重庆东'],
            'tj': ['天津', '天津北', '天津南', '天津西'],
            'nj': ['南京', '南京南', '南京北'],
            'hz': ['杭州', '杭州东', '杭州南'],
            'xa': ['西安', '西安北'],
            'zz': ['郑州', '郑州东', '郑州西'],
            'jn': ['济南', '济南东', '济南西'],
            'sy': ['沈阳', '沈阳北', '沈阳南'],
            'dl': ['大连', '大连北'],
            'km': ['昆明', '昆明南'],
            'gy': ['贵阳', '贵阳北', '贵阳东'],
            'nn': ['南宁', '南宁东', '南宁西'],
            'fz': ['福州', '福州南'],
            'hf': ['合肥', '合肥南', '合肥西'],
            'nc': ['南昌', '南昌西'],
            'sjz': ['石家庄'],
            'ty': ['太原', '太原南'],
            'hrb': ['哈尔滨', '哈尔滨西', '哈尔滨东'],
            'cc': ['长春', '长春西', '长春南'],
            'lm': ['南昌'],
            'yz': ['扬州', '扬州东'],
            'xz': ['徐州', '徐州东'],
            'wz': ['温州', '温州南'],
            'nb': ['宁波'],
            'qd': ['青岛', '青岛北', '青岛西'],
            'xm': ['厦门', '厦门北'],
            'hq': ['海口', '海口东'],
            'sys': ['三亚'],
        }

        # 反向映射：站名 -> 首字母（从 station_dict 构建）
        letter_to_stations = {}
        for station in self.station_names:
            # 获取拼音首字母（从预置映射或从站名推测）
            letters = self._get_station_first_letter(station)
            for letter in letters:
                if letter not in letter_to_stations:
                    letter_to_stations[letter] = []
                if station not in letter_to_stations[letter]:
                    letter_to_stations[letter].append(station)

        # 合并预置映射
        for letter, stations in common_stations.items():
            if letter not in letter_to_stations:
                letter_to_stations[letter] = []
            for station in stations:
                if station in self.station_dict and station not in letter_to_stations[letter]:
                    letter_to_stations[letter].append(station)

        return letter_to_stations

    def _get_station_first_letter(self, station_name: str) -> List[str]:
        """
        获取车站名称的拼音首字母
        简化实现：仅处理常见车站
        :param station_name: 站名
        :return: 首字母列表
        """
        # 常见车站首字母映射
        station_letters = {
            '北京': ['bj', 'beijing'],
            '北京北': ['bjb', 'beijingbei'],
            '北京东': ['bjd', 'beijingdong'],
            '北京南': ['bjn', 'beijingnan'],
            '北京西': ['bjx', 'beijingxi'],
            '北京大兴': ['bjdx', 'beijingdaxing'],
            '北京朝阳': ['bjcy', 'beijingchaoyang'],
            '上海': ['sh', 'shanghai'],
            '上海南': ['shn', 'shanghainan'],
            '上海虹桥': ['shhq', 'shanghaihongqiao'],
            '上海西': ['shx', 'shanghaixi'],
            '广州': ['gz', 'guangzhou'],
            '广州北': ['gzb', 'guangzhoubei'],
            '广州南': ['gzn', 'guangzhounan'],
            '广州东': ['gzd', 'guangzhoudong'],
            '深圳': ['sz', 'shenzhen'],
            '深圳北': ['szb', 'shenzhenbei'],
            '深圳东': ['szd', 'shenzhendong'],
            '深圳西': ['szx', 'shenzhenxi'],
            '长沙': ['cs', 'changsha'],
            '长沙南': ['csn', 'changshanan'],
            '武汉': ['wh', 'wuhan'],
            '武汉东': ['whd', 'wuhandong'],
            '成都': ['cd', 'chengdu'],
            '成都东': ['cdd', 'chengdudong'],
            '重庆': ['cq', 'chongqing'],
            '重庆北': ['cqb', 'chongqingbei'],
            '天津': ['tj', 'tianjin'],
            '南京': ['nj', 'nanjing'],
            '杭州': ['hz', 'hangzhou'],
            '西安': ['xa', 'xian'],
            '郑州': ['zz', 'zhengzhou'],
            '济南': ['jn', 'jinan'],
            '沈阳': ['sy', 'shenyang'],
            '大连': ['dl', 'dalian'],
            '昆明': ['km', 'kunming'],
            '贵阳': ['gy', 'guiyang'],
            '南宁': ['nn', 'nanning'],
            '福州': ['fz', 'fuzhou'],
            '合肥': ['hf', 'hefei'],
            '南昌': ['nc', 'nanchang'],
            '石家庄': ['sjz', 'shijiazhuang'],
            '太原': ['ty', 'taiyuan'],
            '哈尔滨': ['hrb', 'haerbin'],
            '长春': ['cc', 'changchun'],
            '扬州': ['yz', 'yangzhou'],
            '徐州': ['xz', 'xuzhou'],
            '温州': ['wz', 'wenzhou'],
            '宁波': ['nb', 'ningbo'],
            '青岛': ['qd', 'qingdao'],
            '厦门': ['xm', 'xiamen'],
            '海口': ['hk', 'haikou'],
            '三亚': ['sy', 'sanya'],
        }

        # 精确匹配
        if station_name in station_letters:
            return station_letters[station_name]

        # 尝试匹配去掉后缀的情况
        base_name = station_name.rstrip('东西南北')
        if base_name in station_letters:
            return station_letters[base_name]

        # 无匹配时返回站名拼音（简单处理：取每个字的首字母）
        # 这只是一个 fallback，准确度有限
        try:
            return [''.join([c[0].lower() for c in station_name if '\u4e00' <= c <= '\u9fa5'])]
        except Exception:
            # 如果处理失败，返回空列表避免崩溃
            return []

    def search_station(self, keyword: str) -> List[str]:
        """
        搜索车站
        :param keyword: 搜索关键词（支持站名、拼音首字母）
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

        # 3. 首字母匹配
        if keyword_lower in self.first_letter_map:
            for station in self.first_letter_map[keyword_lower]:
                if station in self.station_dict:
                    results.add(station)

        # 4. 如果关键词很短（1-2 字母），尝试作为首字母前缀匹配
        if len(keyword_lower) <= 2:
            for letter, stations in self.first_letter_map.items():
                if letter.startswith(keyword_lower):
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

        # 如果没有找到（可能是输入不完整），尝试模糊匹配
        if not results:
            for station in self.station_names:
                if city_name in station:
                    results.append(station)

        return sorted(list(set(results)))
