"""
通知管理器 - 协调多个通知渠道
"""

import time
from typing import Dict, List
from .base import NotificationChannel, TicketInfo, NotificationConfig


class NotificationManager:
    """通知管理器"""

    def __init__(self, config: Dict):
        """
        初始化通知管理器
        :param config: 通知配置字典
        """
        self.channels: List[NotificationChannel] = []
        self.last_notified: Dict[str, float] = {}  # {train_no: timestamp}
        self.monitored_trains: set = set()  # 新增：已发现的有票车次
        # 只传递 NotificationConfig 定义的参数
        self.config = NotificationConfig(**{
            'enabled': config.get('enabled', True),
            'cooldown_seconds': config.get('cooldown_seconds', 300),
            'only_target_trains': config.get('only_target_trains', False),
            'min_tickets': config.get('min_tickets', 1)
        })

    def register_channel(self, channel: NotificationChannel):
        """
        注册通知渠道
        :param channel: 通知渠道实例
        """
        self.channels.append(channel)

    def notify_ticket_available(self, tickets: List[TicketInfo]) -> Dict[str, Dict[str, str]]:
        """
        发送有票通知
        :param tickets: 有票的车次列表
        :return: 通知结果 {train_no: {channel_name: result}}
        """
        if not self.config.enabled:
            return {}

        # 识别新发现的车次
        current_trains = {ticket.train_no for ticket in tickets}
        new_trains = current_trains - self.monitored_trains

        results = {}
        for ticket in tickets:
            # 判断是否为新票（新票强制通知）
            is_new = ticket.train_no in new_trains
            if self._should_notify(ticket, force_notify=is_new):
                results[ticket.train_no] = self._send_notification(ticket, is_new_ticket=is_new)

        # 更新监控车次集合
        self.monitored_trains.update(current_trains)

        return results

    def _should_notify(self, ticket: TicketInfo, force_notify: bool = False) -> bool:
        """
        判断是否应该发送通知
        :param ticket: 车票信息
        :param force_notify: 是否强制通知（忽略冷却时间）
        :return: 是否应该通知
        """
        # 检查是否只通知目标车次
        if self.config.only_target_trains:
            if not self.config.target_trains or ticket.train_no not in self.config.target_trains:
                return False

        # 冷却时间检查（新票忽略）
        if not force_notify:
            last_time = self.last_notified.get(ticket.train_no, 0)
            if time.time() - last_time < self.config.cooldown_seconds:
                return False

        # 最小余票数量检查
        total_tickets = sum(int(v) if v.isdigit() else 99 for v in ticket.available_seats.values())
        if total_tickets < self.config.min_tickets:
            return False

        return True

    def _send_notification(self, ticket: TicketInfo, is_new_ticket: bool = False) -> Dict[str, str]:
        """
        发送通知到所有可用渠道
        :param ticket: 车票信息
        :param is_new_ticket: 是否为新发现有票的车次
        :return: 各渠道发送结果 {channel_name: result}
        """
        if is_new_ticket:
            title = f"【新发现有票】{ticket.train_no} 有票啦！"
        else:
            title = f"【CRTicketMonitor】{ticket.train_no} 有票啦！"
        message = self._format_ticket_message(ticket)

        results = {}
        for channel in self.channels:
            if channel.is_available():
                try:
                    success = channel.send(title, message, ticket)
                    results[channel.name] = "成功" if success else "失败"
                except Exception as e:
                    results[channel.name] = f"异常: {e}"

        self.last_notified[ticket.train_no] = time.time()
        return results

    def _format_ticket_message(self, ticket: TicketInfo) -> str:
        """
        格式化车票信息为通知消息
        :param ticket: 车票信息
        :return: 格式化的消息字符串
        """
        seats_text = "\n".join([f"  - {k}: {v}" for k, v in ticket.available_seats.items()])
        return f"""车次: {ticket.train_no}
日期: {ticket.date}
路线: {ticket.from_station} → {ticket.to_station}
时间: {ticket.departure_time} (历时: {ticket.duration})
有票坐席:
{seats_text}"""

    def get_available_channels(self) -> List[str]:
        """
        获取可用的通知渠道列表
        :return: 可用渠道名称列表
        """
        return [c.name for c in self.channels if c.is_available()]

    def get_monitored_count(self) -> int:
        """获取当前监控的车次数量"""
        return len(self.monitored_trains)
