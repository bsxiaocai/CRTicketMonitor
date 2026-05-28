"""
后台工作线程
用于异步执行查询、票价获取等耗时操作
"""

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class PriceResultSignal(QObject):
    """票价查询结果信号"""
    finished = Signal(dict)


class PriceWorker(QRunnable):
    """异步票价查询工作线程"""

    def __init__(self, query_service, ticket_data, train_date):
        super().__init__()
        self.query_service = query_service
        self.ticket_data = ticket_data
        self.train_date = train_date
        self.signals = PriceResultSignal()

    @Slot()
    def run(self):
        try:
            from notification.base import TicketInfo
            ticket = TicketInfo(
                train_no=self.ticket_data.get('train_no', ''),
                internal_train_no=self.ticket_data.get('internal_train_no', ''),
                from_station_no=self.ticket_data.get('from_station_no', ''),
                to_station_no=self.ticket_data.get('to_station_no', ''),
                seat_types_code=self.ticket_data.get('seat_types_code', ''),
            )
            result = self.query_service.fetch_single_price(ticket, self.train_date)
            self.signals.finished.emit(result or {})
        except Exception:
            self.signals.finished.emit({})


class QueryResultSignal(QObject):
    """查询结果信号"""
    finished = Signal(dict)
    error = Signal(str)


class QueryWorker(QRunnable):
    """后台查询工作线程"""

    def __init__(self, query_service, date, from_station, to_station, bypass_cache):
        super().__init__()
        self.query_service = query_service
        self.date = date
        self.from_station = from_station
        self.to_station = to_station
        self.bypass_cache = bypass_cache
        self.signals = QueryResultSignal()

    @Slot()
    def run(self):
        try:
            result = self.query_service.execute_query(
                date=self.date,
                from_station=self.from_station,
                to_station=self.to_station,
                bypass_cache=self.bypass_cache
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))


class TransferResultSignal(QObject):
    """中转换乘查询结果信号"""
    finished = Signal(dict)
    error = Signal(str)


class TransferWorker(QRunnable):
    """后台中转换乘查询工作线程"""

    def __init__(self, query_service, date, from_station, to_station):
        super().__init__()
        self.query_service = query_service
        self.date = date
        self.from_station = from_station
        self.to_station = to_station
        self.signals = TransferResultSignal()

    @Slot()
    def run(self):
        try:
            result = self.query_service.execute_transfer_query(
                date=self.date,
                from_station=self.from_station,
                to_station=self.to_station
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
