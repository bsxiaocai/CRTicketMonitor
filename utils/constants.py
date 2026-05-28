"""共享常量"""

# 中文席位名到内部 key 的映射
SEAT_NAMES = {
    'business': '商/特',
    'first': '一等座',
    'second': '二等座',
    'soft_sleeper': '一等/软卧',
    'hard_sleeper': '二等/硬卧',
    'soft_seat': '软座',
    'hard_seat': '硬座',
    'no_seat': '无座',
}

# 无票哨兵值集合
SEAT_SENTINEL = frozenset({'无', '--', '', '0'})
