"""
监控任务管理服务
支持同时监控多个查询任务
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
import threading
import time

# 尝试导入 PySide6，如果失败则使用 threading.Timer 降级方案
try:
    from PySide6.QtCore import QTimer, QObject, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QTimer = None
    QObject = None
    Signal = None


@dataclass
class MonitorTask:
    """监控任务数据类"""
    task_id: str
    from_station: str
    to_station: str
    date: str
    target_trains: List[str]
    interval_seconds: int = 30
    is_active: bool = False
    name: str = ""  # 可选的任务名称

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.from_station} → {self.to_station}"


if PYSIDE6_AVAILABLE:
    class MonitorTaskRunner(QObject):
        """监控任务执行器（使用 PySide6 QTimer）"""
        tick = Signal()

        def __init__(self, interval_seconds: int):
            super().__init__()
            self.timer = QTimer()
            self.timer.setInterval(interval_seconds * 1000)
            self.timer.timeout.connect(self.tick.emit)

        def start(self):
            self.timer.start()

        def stop(self):
            self.timer.stop()

        def set_interval(self, seconds: int):
            self.timer.setInterval(seconds * 1000)
else:
    class MonitorTaskRunner:
        """监控任务执行器（降级版，使用 threading）"""

        def __init__(self, interval_seconds: int):
            self._interval = interval_seconds
            self._interval_lock = threading.Lock()
            self._stop_event = threading.Event()
            self._thread = None
            self._callbacks = []
            self._callbacks_lock = threading.Lock()

        def start(self):
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

        def stop(self):
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)

        def set_interval(self, seconds: int):
            with self._interval_lock:
                self._interval = seconds

        def _run(self):
            while not self._stop_event.is_set():
                with self._interval_lock:
                    interval = self._interval
                self._stop_event.wait(timeout=interval)
                if not self._stop_event.is_set():
                    with self._callbacks_lock:
                        callbacks = list(self._callbacks)
                    for cb in callbacks:
                        cb()

        def connect(self, callback):
            with self._callbacks_lock:
                self._callbacks.append(callback)

        def disconnect(self, callback):
            with self._callbacks_lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)


class MonitorManager:
    """监控任务管理器"""

    def __init__(self):
        """初始化监控管理器"""
        self.tasks: Dict[str, MonitorTask] = {}
        self.runners: Dict[str, MonitorTaskRunner] = {}
        self.callbacks: Dict[str, Callable] = {}

    def create_task(self, from_station: str, to_station: str, date: str,
                    target_trains: List[str] = None, interval_seconds: int = 30,
                    name: str = "") -> str:
        """
        创建监控任务
        :param from_station: 始发站
        :param to_station: 到达站
        :param date: 出发日期
        :param target_trains: 目标车次列表
        :param interval_seconds: 查询间隔（秒）
        :param name: 任务名称
        :return: 任务 ID
        """
        task_id = str(uuid.uuid4())[:8]
        task = MonitorTask(
            task_id=task_id,
            from_station=from_station,
            to_station=to_station,
            date=date,
            target_trains=target_trains or [],
            interval_seconds=interval_seconds,
            is_active=False,
            name=name
        )
        self.tasks[task_id] = task

        # 创建定时器
        runner = MonitorTaskRunner(interval_seconds)
        self.runners[task_id] = runner

        return task_id

    def remove_task(self, task_id: str) -> bool:
        """
        删除监控任务
        :param task_id: 任务 ID
        :return: 是否删除成功
        """
        if task_id in self.tasks:
            self.stop_task(task_id)
            del self.tasks[task_id]
            if task_id in self.runners:
                del self.runners[task_id]
            if task_id in self.callbacks:
                del self.callbacks[task_id]
            return True
        return False

    def start_task(self, task_id: str, callback: Callable = None) -> bool:
        """
        启动监控任务
        :param task_id: 任务 ID
        :param callback: 回调函数
        :return: 是否启动成功
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        runner = self.runners[task_id]

        # 设置回调
        if callback:
            self.callbacks[task_id] = callback
            if hasattr(runner, 'tick'):
                runner.tick.connect(callback)
            elif hasattr(runner, 'connect'):
                runner.connect(callback)

        # 更新状态
        task.is_active = True
        runner.start()

        return True

    def stop_task(self, task_id: str) -> bool:
        """
        停止监控任务
        :param task_id: 任务 ID
        :return: 是否停止成功
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        runner = self.runners[task_id]

        # 断开回调
        if task_id in self.callbacks:
            callback = self.callbacks[task_id]
            if hasattr(runner, 'tick'):
                runner.tick.disconnect(callback)
            elif hasattr(runner, 'disconnect'):
                runner.disconnect(callback)
            del self.callbacks[task_id]

        # 更新状态
        task.is_active = False
        runner.stop()

        return True

    def toggle_task(self, task_id: str, callback: Callable = None) -> bool:
        """
        切换任务状态
        :param task_id: 任务 ID
        :param callback: 回调函数（启动时需要）
        :return: 启动后的状态
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        if task.is_active:
            self.stop_task(task_id)
            return False
        else:
            self.start_task(task_id, callback)
            return True

    def update_task_interval(self, task_id: str, interval_seconds: int) -> bool:
        """
        更新任务查询间隔
        :param task_id: 任务 ID
        :param interval_seconds: 新的间隔（秒）
        :return: 是否更新成功
        """
        if task_id in self.tasks:
            self.tasks[task_id].interval_seconds = interval_seconds
            if task_id in self.runners:
                self.runners[task_id].set_interval(interval_seconds)
            return True
        return False

    def get_task(self, task_id: str) -> Optional[MonitorTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[MonitorTask]:
        """获取所有任务"""
        return list(self.tasks.values())

    def get_active_tasks(self) -> List[MonitorTask]:
        """获取所有活动任务"""
        return [t for t in self.tasks.values() if t.is_active]

    def stop_all_tasks(self):
        """停止所有任务"""
        for task_id in list(self.tasks.keys()):
            self.stop_task(task_id)

    def is_task_active(self, task_id: str) -> bool:
        """检查任务是否正在运行"""
        return task_id in self.tasks and self.tasks[task_id].is_active
