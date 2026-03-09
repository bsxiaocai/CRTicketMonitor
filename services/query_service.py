"""
查询服务模块
负责整合查询流程，协调 API、解析、筛选、排序等功能
"""

from typing import List, Dict, Optional
from datetime import datetime


class QueryService:
    """查询服务"""

    def __init__(self, ticket_api, ticket_parser, train_classifier, logger, query_history,
                 notification_manager, config_manager=None, cache_service=None):
        """
        初始化查询服务
        :param ticket_api: TicketAPI 实例
        :param ticket_parser: TicketParser 实例
        :param train_classifier: TrainClassifier 实例
        :param logger: 日志记录器
        :param query_history: 查询历史记录器
        :param notification_manager: 通知管理器
        :param config_manager: 配置管理器（用于 D/C 识别模式）
        :param cache_service: 缓存服务（可选）
        """
        self.ticket_api = ticket_api
        self.ticket_parser = ticket_parser
        self.train_classifier = train_classifier
        self.logger = logger
        self.query_history = query_history
        self.notification_manager = notification_manager
        self.config_manager = config_manager
        self.cache_service = cache_service

    def execute_query(self, date: str, from_station: str, to_station: str,
                     target_trains: List[str] = None, filters: Dict = None,
                     quick_mode: bool = False) -> Dict:
        """
        执行完整查询流程
        :param date: 出发日期
        :param from_station: 始发站
        :param to_station: 到达站
        :param target_trains: 目标车次列表
        :param filters: 筛选参数 {'type', 'from', 'to', 'time_period', 'sort'}
        :param quick_mode: 快速模式，跳过统计信息（仅用于快速显示）
        :return: {'table': str, 'tickets': List[TicketInfo], 'all_tickets': List[TicketInfo], 'notification_results': Dict}
        """
        if filters is None:
            filters = {}

        # 检查缓存
        use_cache = False
        raw_data = None
        if self.cache_service:
            raw_data = self.cache_service.get(from_station, to_station, date)
            if raw_data is not None:
                use_cache = True
                self.logger.debug(f"使用缓存数据：{from_station} -> {to_station} ({date})")

        # 执行查询（如果缓存未命中）
        if not use_cache:
            raw_data = self.ticket_api.query_tickets(date, from_station, to_station)

        if raw_data == "STATION_NOT_FOUND":
            return {"error": "STATION_NOT_FOUND", "table": "", "tickets": [], "all_tickets": [], "total_count": 0, "available_count": 0}
        if raw_data is None:
            return {"error": "QUERY_FAILED", "table": "", "tickets": [], "all_tickets": [], "total_count": 0, "available_count": 0}

        # 写入缓存
        if self.cache_service and not use_cache:
            self.cache_service.set(from_station, to_station, date, raw_data)

        # 准备分类函数 - 传入正确的配置
        def classify_wrapper(train_no):
            config = self.config_manager.get_config() if self.config_manager else {}
            return self.train_classifier.classify_train(train_no, config)

        # 解析数据 - 使用 return_table=True 获取表格字符串
        table_str, all_tickets = self.ticket_parser.parse_and_print(
            raw_data=raw_data,
            ticket_info_list=[],
            target_trains=target_trains,
            type_filter=filters.get('type'),
            sel_from=filters.get('from'),
            sel_to=filters.get('to'),
            date=date,
            time_period=filters.get('time_period'),
            sort_type=filters.get('sort'),
            station_dict=self.ticket_api.station_dict,
            code_to_name=self.ticket_api.code_to_name,
            classify_func=classify_wrapper,
            return_table=True,
            return_all=True
        )

        # 快速模式：只返回基本信息，不统计详细信息
        if quick_mode:
            return {
                "table": table_str,
                "tickets": [],
                "all_tickets": all_tickets,
                "notification_results": {},
                "total_count": len(raw_data),
                "available_count": 0  # 快速模式不统计
            }

        # 有票车次
        available_tickets = [t for t in all_tickets if t.available_seats]

        # 记录查询历史
        if self.query_history:
            train_list = [t.train_no for t in available_tickets]
            self.query_history.record(from_station, to_station, date, len(raw_data), train_list)

        # 发送通知（仅监控模式）
        notification_results = {}
        if self.notification_manager and available_tickets:
            monitored_before = self.notification_manager.get_monitored_count()
            notification_results = self.notification_manager.notify_ticket_available(available_tickets)
            monitored_after = self.notification_manager.get_monitored_count()
            new_count = monitored_after - monitored_before

            self.logger.info(f"发现 {len(available_tickets)} 个有票车次：{[t.train_no for t in available_tickets]}")
            if new_count > 0:
                self.logger.info(f"新发现 {new_count} 个有票车次")

        return {
            "table": table_str,
            "tickets": available_tickets,
            "all_tickets": all_tickets,
            "notification_results": notification_results,
            "total_count": len(raw_data),
            "available_count": len(available_tickets)
        }
