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
    arrival_time: str      # 到达时间
    duration: str          # 历时
    available_seats: Dict[str, str]  # {坐席类型: 余票数量}
    internal_train_no: str = ""      # 内部车次号（d[2]，票价API必需）
    from_station_no: str = ""        # 出发站序号（d[16]）
    to_station_no: str = ""          # 到达站序号（d[17]）
    seat_types_code: str = ""        # 席别代码串（d[35]）
    prices: Optional[Dict[str, str]] = None  # {席别显示名: 价格字符串}

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class TransferTicketInfo:
    """中转换乘车票信息"""
    first_leg: TicketInfo        # 第一程
    second_leg: TicketInfo       # 第二程
    transfer_station: str        # 中转站名称
    total_duration: str          # 总历时
    wait_time: str               # 中转等待时间

    def to_dict(self) -> dict:
        return {
            'first_leg': self.first_leg.to_dict(),
            'second_leg': self.second_leg.to_dict(),
            'transfer_station': self.transfer_station,
            'total_duration': self.total_duration,
            'wait_time': self.wait_time,
        }


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
