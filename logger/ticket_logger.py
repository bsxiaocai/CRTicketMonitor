"""
日志系统配置和工具
"""

import os
import logging
import platform
from logging.handlers import RotatingFileHandler
from typing import Optional


class TicketLogger:
    """车票监控日志器"""

    def __init__(self, log_dir: str, config: dict):
        """
        初始化日志器
        :param log_dir: 日志目录路径
        :param config: 日志配置字典
        """
        self.log_dir = log_dir
        self.config = config
        os.makedirs(log_dir, exist_ok=True)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """配置日志系统"""
        level_str = self.config.get("level", "INFO")
        level = getattr(logging, level_str, logging.INFO)
        max_size = self.config.get("max_size_mb", 10) * 1024 * 1024
        backup_count = self.config.get("backup_count", 5)
        console_output = self.config.get("console_output", False)

        # 主日志文件
        log_file = os.path.join(self.log_dir, "ticket_monitor.log")
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )

        # 错误日志单独文件
        error_log_file = os.path.join(self.log_dir, "error.log")
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)

        # 格式化
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        # 配置logger
        logger = logging.getLogger('CRTicketMonitor')
        logger.setLevel(level)
        # 清除已有的handler
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.addHandler(error_handler)

        # 同时输出到控制台
        if console_output or level == logging.DEBUG:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def log_startup(self, version: str = "1.2.0"):
        """记录启动信息"""
        self.logger.info("=" * 60)
        self.logger.info("CRTicketMonitor 启动")
        self.logger.info(f"版本: {version}")
        self.logger.info(f"操作系统: {platform.system()} {platform.release()}")

    def log_shutdown(self):
        """记录关闭信息"""
        self.logger.info("CRTicketMonitor 退出")
        self.logger.info("=" * 60)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str, exc_info: bool = False):
        self.logger.error(msg, exc_info=exc_info)

    def critical(self, msg: str, exc_info: bool = True):
        self.logger.critical(msg, exc_info=exc_info)
