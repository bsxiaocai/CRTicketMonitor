"""
时段筛选器
负责车次发车时段的筛选
"""

class TimeFilter:
    """时段筛选器"""

    @staticmethod
    def filter_by_time_period(departure_time: str, period: int = None) -> bool:
        """
        时段筛选（模仿12306）
        将一天分为4个时段：00:00-06:00, 06:00-12:00, 12:00-18:00, 18:00-24:00
        :param departure_time: 车次发车时间（格式：HH:MM）
        :param period: 时段（None=全部, 0=00:00-06:00, 1=06:00-12:00, 2=12:00-18:00, 3=18:00-24:00）
        :return: 是否保留该车次
        """
        if period is None:
            return True  # 不筛选

        try:
            hour = int(departure_time.split(':')[0])
            if period == 0:
                return 0 <= hour < 6
            elif period == 1:
                return 6 <= hour < 12
            elif period == 2:
                return 12 <= hour < 18
            elif period == 3:
                return 18 <= hour < 24
            return False
        except Exception:
            return True  # 解析失败时保留
