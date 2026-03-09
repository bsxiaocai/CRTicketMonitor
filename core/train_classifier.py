"""
车次分类器
负责智能识别车次类型（高铁动车/普通车）以及复兴号、智能动车组标识
"""

import re


class TrainClassifier:
    """车次分类器"""

    # 复兴号号段（根据 12306 常见号段）
    FUXING_RANGES = [
        # G 字头复兴号
        ('G', 1, 498),      # G1-G498
        ('G', 5001, 5998),  # G5001-G5998
        ('G', 9001, 9999),  # G9001-G9999
        # D 字头复兴号
        ('D', 1, 498),      # D1-D498
        ('D', 9001, 9999),  # D9001-D9999
        # C 字头部分
        ('C', 2001, 2999),  # C2001-C2999
    ]

    # 智能动车组号段
    SMART_RANGES = [
        # G 字头智能动车组
        ('G', 8, 9),        # G8、G9 开头
        ('G', 80, 89),      # G80xx-G89xx
        ('G', 4001, 4098),  # G4001-G4098
        ('G', 8001, 8098),  # G8001-G8098
        # D 字头智能动车组
        ('D', 901, 950),    # D901-D950
    ]

    @staticmethod
    def classify_train(train_no: str, config: dict = None) -> str:
        """
        判断车次类型（用于 GC/D/Z/T/K 分类）
        :param train_no: 车次号
        :param config: 配置字典（可选）
        :return: "GC" | "D" | "Z" | "T" | "K" | "其他"
        """
        if config is None:
            config = {}

        prefix = train_no[0].upper() if train_no else ''

        if prefix in ['G', 'C']:
            return "GC"
        elif prefix == 'D':
            return "D"
        elif prefix == 'Z':
            return "Z"
        elif prefix == 'T':
            return "T"
        elif prefix == 'K':
            return "K"
        else:
            return "其他"

    @staticmethod
    def is_fuxing(train_no: str) -> bool:
        """
        判断是否为复兴号
        :param train_no: 车次号
        :return: 是否为复兴号
        """
        if not train_no or len(train_no) < 2:
            return False

        prefix = train_no[0].upper()
        num_part = re.search(r'\d+', train_no)
        if not num_part:
            return False
        number = int(num_part.group())

        for p, start, end in TrainClassifier.FUXING_RANGES:
            if prefix == p and start <= number <= end:
                return True
        return False

    @staticmethod
    def is_smart(train_no: str) -> bool:
        """
        判断是否为智能动车组
        :param train_no: 车次号
        :return: 是否为智能动车组
        """
        if not train_no or len(train_no) < 2:
            return False

        prefix = train_no[0].upper()
        num_part = re.search(r'\d+', train_no)
        if not num_part:
            return False
        number = int(num_part.group())

        # 特殊号段判断（十位数判断）
        if prefix == 'G' and number < 100:
            # G8, G9
            if number in [8, 9]:
                return True
        if prefix == 'G' and 1000 <= number < 10000:
            # G40xx, G80xx
            thousand = number // 100
            if thousand in [40, 80]:
                return True

        for p, start, end in TrainClassifier.SMART_RANGES:
            if prefix == p and start <= number <= end:
                return True
        return False

    @staticmethod
    def get_train_prefix(train_no: str) -> str:
        """获取车次前缀字母"""
        if not train_no:
            return ""
        match = re.match(r'([A-Za-z]+)', train_no)
        return match.group(1).upper() if match else ""

    @staticmethod
    def get_train_number(train_no: str) -> int:
        """获取车次数字部分"""
        if not train_no:
            return 9999
        num_part = re.search(r'\d+', train_no)
        return int(num_part.group()) if num_part else 9999
