"""
车次分类器
负责智能识别车次类型（高铁动车/普通车）
"""

import re


class TrainClassifier:
    """车次分类器"""

    @staticmethod
    def classify_train(train_no: str, config: dict) -> str:
        """
        判断车次类型
        :param train_no: 车次号
        :param config: 配置字典
        :return: "高铁动车" | "普通车" | "其他"
        """
        dc_config = config.get("dc_classification", {})

        # 自定义映射优先
        if train_no in dc_config.get("custom_mapping", {}):
            return dc_config["custom_mapping"][train_no]

        prefix = train_no[0].upper()
        num_part = re.search(r'\d+', train_no)
        number = int(num_part.group()) if num_part else 9999

        if prefix in ['K', 'T', 'Z'] or train_no.isdigit():
            return "普通车"
        if prefix == 'G':
            return "高铁动车"
        if prefix in ['D', 'C']:
            if dc_config.get("default_mode") == "official":
                return "高铁动车"
            # 智能识别模式
            return "普通车" if number <= dc_config.get("smart_threshold", 899) else "高铁动车"
        return "其他"
