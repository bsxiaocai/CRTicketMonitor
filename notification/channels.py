"""
各种通知渠道的具体实现
"""

import os
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Optional
from .base import NotificationChannel, TicketInfo


class WindowsDesktopNotification(NotificationChannel):
    """Windows 桌面通知 (使用 win10toast)"""

    def __init__(self, icon_path: Optional[str] = None):
        self._toaster = None
        self._icon_path = icon_path
        self._init_toaster()

    def _init_toaster(self):
        try:
            from win10toast import ToastNotifier
            self._toaster = ToastNotifier()
        except ImportError:
            self._toaster = None

    @property
    def name(self) -> str:
        return "Windows桌面通知"

    def send(self, title: str, message: str, ticket_info: Optional[TicketInfo] = None) -> bool:
        if not self._toaster:
            return False

        try:
            self._toaster.show_toast(
                title=title,
                msg=message,
                icon_path=self._icon_path if self._icon_path and os.path.exists(self._icon_path) else None,
                duration=5,
                threaded=True
            )
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        return self._toaster is not None


class WeChatWorkNotification(NotificationChannel):
    """企业微信机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "企业微信"

    def send(self, title: str, message: str, ticket_info: Optional[TicketInfo] = None) -> bool:
        if not self.webhook_url:
            return False

        try:
            import requests
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {title}\n{message}"
                }
            }
            response = requests.post(self.webhook_url, json=data, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        return bool(self.webhook_url)


class FeishuNotification(NotificationChannel):
    """飞书机器人通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "飞书"

    def send(self, title: str, message: str, ticket_info: Optional[TicketInfo] = None) -> bool:
        if not self.webhook_url:
            return False

        try:
            import requests
            data = {
                "msg_type": "post",
                "content": {
                    "post": {
                        "zh_cn": {
                            "title": title,
                            "content": [[{"tag": "text", "text": message}]]
                        }
                    }
                }
            }
            response = requests.post(self.webhook_url, json=data, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def is_available(self) -> bool:
        return bool(self.webhook_url)


class DingTalkNotification(NotificationChannel):
    """钉钉机器人通知"""

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret

    @property
    def name(self) -> str:
        return "钉钉"

    def send(self, title: str, message: str, ticket_info: Optional[TicketInfo] = None) -> bool:
        if not self.webhook_url:
            return False

        try:
            import requests
            # 如果配置了签名，计算签名
            url = self.webhook_url
            if self.secret:
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{self.secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"### {title}\n{message}"
                }
            }
            response = requests.post(url, json=data, timeout=5)
            result = response.json()
            return result.get('errcode') == 0
        except Exception:
            return False

    def is_available(self) -> bool:
        return bool(self.webhook_url)
