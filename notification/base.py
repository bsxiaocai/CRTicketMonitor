"""
通知系统基类和数据类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class TicketInfo:
    """车票信息数据类"""
    train_no: str          # 车次号
    from_station: str      # 始发站
    to_station: str        # 到达站
    date: str              # 出发日期
    departure_time: str    # 开车时间
    duration: str          # 历时
    available_seats: Dict[str, str]  # {坐席类型: 余票数量}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class NotificationConfig:
    """通知配置数据类"""
    enabled: bool                   # 是否启用
    cooldown_seconds: int           # 冷却时间（防重复通知）
    only_target_trains: bool       # 仅通知目标车次
    min_tickets: int              # 最小余票数量才通知
    target_trains: Optional[List[str]] = None  # 目标车次列表


class NotificationChannel(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    def send(self, title: str, message: str, ticket_info: Optional[TicketInfo] = None) -> bool:
        """
        发送通知
        :param title: 通知标题
        :param message: 通知内容
        :param ticket_info: 车票信息（可选）
        :return: 是否发送成功
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查渠道是否可用"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """获取渠道名称"""
        pass
