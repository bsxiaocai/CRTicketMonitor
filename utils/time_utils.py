"""时间工具函数"""


def time_to_minutes(t: str) -> int:
    """将 HH:MM 格式转换为分钟数"""
    try:
        h, m = map(int, t.split(':'))
        return h * 60 + m
    except Exception:
        return 99999


def duration_to_minutes(d: str) -> int:
    """将历时转换为分钟数（支持 HH:MM 和 X 小时 X 分格式）"""
    try:
        if ':' in d:
            h, m = map(int, d.split(':'))
            return h * 60 + m
        else:
            h = 0
            m = 0
            if '小时' in d:
                parts = d.split('小时')
                h = int(parts[0])
                if len(parts) > 1 and '分' in parts[1]:
                    m = int(parts[1].replace('分', ''))
            elif '分' in d:
                m = int(d.replace('分', ''))
            else:
                return int(d) * 60
            return h * 60 + m
    except Exception:
        return 99999


def is_cross_day(departure: str, arrival: str, duration: str) -> bool:
    """检测是否跨天运行"""
    dep = time_to_minutes(departure)
    arr = time_to_minutes(arrival)
    dur = duration_to_minutes(duration)
    return arr < dep and dur > 0
