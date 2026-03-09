"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
import os


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG = {
        "dc_classification": {
            "default_mode": "official",
            "smart_threshold": 899,
            "custom_mapping": {}
        },
        "notification": {
            "enabled": True,
            "cooldown_seconds": 300,
            "only_target_trains": False,
            "min_tickets": 1
        },
        "logging": {
            "level": "INFO",
            "max_size_mb": 10,
            "backup_count": 5,
            "console_output": False,
            "log_query_history": True
        },
        "auto_open_12306": False,
        "gui": {
            "default_monitor_interval": 30,
            "theme": "light"
        }
    }

    def __init__(self, config_path: str):
        """
        初始化配置管理器
        :param config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self) -> dict:
        """
        加载配置文件
        :return: 配置字典
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # 深度合并配置，保持默认值
                    self._deep_update(self.config, loaded_config)
            except Exception as e:
                print(f"警告: 配置文件读取失败，使用默认配置: {e}")
        else:
            # 保存默认配置
            self.save_config()

        return self.config

    def save_config(self) -> None:
        """
        保存配置文件
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"错误: 配置文件保存失败: {e}")

    def _deep_update(self, d: dict, u: dict) -> dict:
        """
        深度合并字典
        :param d: 目标字典
        :param u: 源字典
        :return: 合并后的字典
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d

    def get(self, key: str, default=None):
        """
        获取配置项
        :param key: 配置键（支持点号访问，如 "notification.enabled"）
        :param default: 默认值
        :return: 配置值
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        """
        设置配置项
        :param key: 配置键（支持点号访问）
        :param value: 配置值
        """
        keys = key.split('.')
        current = self.config
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def get_config(self) -> dict:
        """获取完整配置"""
        return self.config

    def set_config(self, config: dict):
        """设置完整配置"""
        self.config = config
