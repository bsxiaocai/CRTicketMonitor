"""
通知系统模块
"""

from .base import TicketInfo, NotificationChannel, NotificationConfig
from .manager import NotificationManager
from .channels import (
    WindowsDesktopNotification,
    WeChatWorkNotification,
    FeishuNotification,
    DingTalkNotification
)

__all__ = [
    'TicketInfo',
    'NotificationChannel',
    'NotificationConfig',
    'NotificationManager',
    'WindowsDesktopNotification',
    'WeChatWorkNotification',
    'FeishuNotification',
    'DingTalkNotification',
]
