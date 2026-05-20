"""
12306 余票监控工具 - GUI 主窗口
PySide6 实现
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QGroupBox, QCheckBox, QSpinBox, QComboBox,
    QTextEdit, QFrame, QTabWidget, QMenuBar, QMenu, QApplication, QListWidget,
    QDialog, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QDate, Signal
from PySide6.QtGui import QColor, QFont, QAction

from ui.gui.filter_panel import FilterPanel
from core.train_classifier import TrainClassifier


class QueryResultWidget(QWidget):
    """查询结果表格组件"""

    ticket_double_clicked = Signal(str)  # 车次号（双击时触发）
    unfavorite_requested = Signal(str)  # 取消收藏请求（右键菜单触发）

    def __init__(self):
        super().__init__()
        self.favorites = []  # 当前收藏列表
        self.current_data = []  # 当前表格数据（用于排序和筛选）
        self.filtered_data = []  # 筛选后的数据
        self.sort_column = -1  # 当前排序列
        self.sort_order = Qt.AscendingOrder  # 当前排序顺序
        self.filter_config = {}  # 当前筛选配置
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(14)  # 去掉"类型"列
        self.table.setHorizontalHeaderLabels([
            "车次", "出发站", "到达站", "开点", "到点", "历时",
            "商务座/特等座", "一等座", "二等座", "软卧/动卧/一等卧", "硬卧/二等卧", "软座", "硬座", "无座"
        ])

        # 设置列宽 - 均匀分布
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # 启用表头点击排序
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)

        # 启用双击
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

    def _on_header_clicked(self, logical_index):
        """处理表头点击事件"""
        # logical_index: 3=开点，4=到点，5=历时
        # 只允许点击 3-5 列（开点、到点、历时）进行排序
        if logical_index in [3, 4, 5]:
            # 切换排序顺序
            if self.sort_column == logical_index:
                self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
            else:
                self.sort_column = logical_index
                self.sort_order = Qt.AscendingOrder

            # 执行排序
            self._sort_data(logical_index)

            # 更新表头显示（添加排序箭头）
            self._update_header_labels()

    def _time_to_minutes(self, t: str) -> int:
        """将 HH:MM 格式转换为分钟数"""
        try:
            h, m = map(int, t.split(':'))
            return h * 60 + m
        except Exception:
            return 99999

    def _duration_to_minutes(self, d: str) -> int:
        """将历时转换为分钟数（支持 HH:MM 和 X 小时 X 分格式）"""
        try:
            if ':' in d:
                h, m = map(int, d.split(':'))
                return h * 60 + m
            else:
                # 处理 "X 小时 X 分" 格式
                h = 0
                m = 0
                if '小时' in d:
                    parts = d.split('小时')
                    h = int(parts[0])
                    if len(parts) > 1 and '分' in parts[1]:
                        m = int(parts[1].replace('分', ''))
                elif '分' in d:
                    m = int(d.replace('分', ''))
                else:
                    return int(d) * 60  # 纯数字按小时算
                return h * 60 + m
        except Exception:
            return 99999

    def _sort_data(self, column):
        """执行排序"""
        if not self.current_data:
            return

        # 定义排序键函数
        def get_sort_key(item):
            # 收藏车次优先的标记
            is_favorite = item['train_no'].upper() in [f.upper() for f in self.favorites]
            fav_priority = 0 if is_favorite else 1

            if column == 3:  # 开点
                time_val = self._time_to_minutes(item.get('departure_time', '99:99'))
                return (fav_priority, time_val)
            elif column == 4:  # 到点
                time_val = self._time_to_minutes(item.get('arrival_time', '99:99'))
                return (fav_priority, time_val)
            elif column == 5:  # 历时
                duration_val = self._duration_to_minutes(item.get('duration', '99:99'))
                return (fav_priority, duration_val)
            return (fav_priority, 0)

        # 排序
        reverse = (self.sort_order == Qt.DescendingOrder)
        self.current_data.sort(key=get_sort_key, reverse=reverse)

        # 重新应用筛选（排序可能改变顺序）
        self._filter_data()

        # 刷新表格显示
        self._refresh_table()

    def _update_header_labels(self):
        """更新表头标签，显示排序箭头"""
        labels = ["车次", "出发站", "到达站", "开点", "到点", "历时",
                  "商务座/特等座", "一等座", "二等座", "软卧/动卧/一等卧", "硬卧/二等卧", "软座", "硬座", "无座"]

        for i in range(len(labels)):
            if i == self.sort_column:
                arrow = " ▲" if self.sort_order == Qt.AscendingOrder else " ▼"
                self.table.horizontalHeaderItem(i).setText(labels[i] + arrow)
            else:
                self.table.horizontalHeaderItem(i).setText(labels[i])

    def apply_filters(self, filter_config: dict):
        """应用筛选条件"""
        self.filter_config = filter_config
        # 只有在有筛选配置且配置不为空时才应用筛选
        if filter_config:
            self._filter_data()
        else:
            # 没有筛选配置时，显示全部
            self.filtered_data = self.current_data.copy()
        self._refresh_table()

    def _filter_data(self):
        """筛选数据（修复席别筛选、时段筛选和车型筛选）"""
        self.filtered_data = []

        # 获取筛选配置
        train_types = self.filter_config.get('train_types', [])
        from_stations = self.filter_config.get('from_stations', [])
        to_stations = self.filter_config.get('to_stations', [])
        seat_types = self.filter_config.get('seat_types', [])
        time_period = self.filter_config.get('time_period', '00:00-24:00')
        show_fuxing = self.filter_config.get('show_fuxing', True)
        show_smart = self.filter_config.get('show_smart', True)

        for item in self.current_data:
            # 车次类型筛选
            train_type = item.get('train_type', '其他')
            if train_types and train_type not in train_types:
                continue

            # 出发站筛选
            from_station = item.get('from_station', '')
            if from_stations and from_station not in from_stations:
                continue

            # 到达站筛选
            to_station = item.get('to_station', '')
            if to_stations and to_station not in to_stations:
                continue

            # 席别筛选 - 修复字段映射
            has_seat = False
            seat_mapping = {
                'business': item.get('business_seat', '--'),
                'first': item.get('first_seat', '--'),
                'second': item.get('second_seat', '--'),
                'soft_sleeper': item.get('soft_sleeper', '--'),  # 软卧/动卧/一等卧
                'hard_sleeper': item.get('hard_sleeper', '--'),  # 硬卧/二等卧
                'soft_seat': item.get('soft_seat', '--'),  # 软座
                'hard_seat': item.get('hard_seat', '--'),  # 硬座
                'no_seat': item.get('no_seat', '--'),
            }

            # 检查是否有选中的席别有票
            for seat_key in seat_types:
                seat_value = seat_mapping.get(seat_key, '--')
                if seat_value not in ['--', '', '无', '0', '无票']:
                    has_seat = True
                    break

            # 如果勾选了席别但没有匹配的席别有票，过滤掉该车次
            if seat_types and not has_seat:
                continue

            # 发车时段筛选
            if time_period != '00:00-24:00':
                departure_time = item.get('departure_time', '')
                if departure_time and departure_time != '--':
                    try:
                        h = int(departure_time.split(':')[0])
                        start, end = time_period.split('-')
                        start_h = int(start.split(':')[0])
                        end_h = int(end.split(':')[0])
                        if not (start_h <= h < end_h):
                            continue
                    except Exception:
                        pass

            # 复兴号/智能动车组筛选
            is_fuxing = item.get('is_fuxing', False)
            is_smart = item.get('is_smart', False)

            # 如果不显示复兴号且该车次是复兴号，过滤掉
            if not show_fuxing and is_fuxing:
                continue

            # 如果不显示智能动车组且该车次是智能动车组，过滤掉
            if not show_smart and is_smart:
                continue

            self.filtered_data.append(item)

    def _refresh_table(self):
        """刷新表格显示（不改变数据）"""
        self.table.setRowCount(0)

        # 始终使用 filtered_data 显示
        data_to_show = self.filtered_data if self.filtered_data else self.current_data

        for ticket in data_to_show:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            train_no = ticket['train_no']
            has_ticket = ticket.get('has_ticket', False)
            is_favorite = train_no.upper() in [f.upper() for f in self.favorites]

            # 构建车次显示（含"复"、"智"标识，用小字）
            train_display = train_no
            if ticket.get('is_fuxing', False):
                train_display += " 复"
            if ticket.get('is_smart', False):
                train_display += " 智"

            # 设置数据 - 注意列索引变化（去掉类型列后）
            self.table.setItem(row_position, 0, QTableWidgetItem(train_display))
            self.table.setItem(row_position, 1, QTableWidgetItem(ticket.get('from_station', '--')))
            self.table.setItem(row_position, 2, QTableWidgetItem(ticket.get('to_station', '--')))
            self.table.setItem(row_position, 3, QTableWidgetItem(ticket.get('departure_time', '--')))
            self.table.setItem(row_position, 4, QTableWidgetItem(ticket.get('arrival_time', '--')))
            self.table.setItem(row_position, 5, QTableWidgetItem(ticket.get('duration', '--')))
            self.table.setItem(row_position, 6, QTableWidgetItem(ticket.get('business_seat', '--')))
            self.table.setItem(row_position, 7, QTableWidgetItem(ticket.get('first_seat', '--')))
            self.table.setItem(row_position, 8, QTableWidgetItem(ticket.get('second_seat', '--')))
            self.table.setItem(row_position, 9, QTableWidgetItem(ticket.get('soft_sleeper', '--')))
            self.table.setItem(row_position, 10, QTableWidgetItem(ticket.get('hard_sleeper', '--')))
            self.table.setItem(row_position, 11, QTableWidgetItem(ticket.get('soft_seat', '--')))
            self.table.setItem(row_position, 12, QTableWidgetItem(ticket.get('hard_seat', '--')))
            self.table.setItem(row_position, 13, QTableWidgetItem(ticket.get('no_seat', '--')))

            # 应用颜色
            self._apply_row_color(row_position, has_ticket, is_favorite)

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        row = self.table.rowAt(pos.y())
        if row < 0:
            return

        train_no_item = self.table.item(row, 0)
        if not train_no_item:
            return

        # 获取车次号（去除"复"、"智"标识和空格）
        train_no_raw = train_no_item.text().strip()
        train_no_clean = train_no_raw.split()[0]
        # 去除颜色标记
        train_no_clean = train_no_clean.replace('\033[92m', '').replace('\033[93m', '').replace('\033[90m', '').replace('\033[0m', '')

        # 检查是否已收藏
        is_favorite = train_no_clean.upper() in [f.upper() for f in self.favorites]

        menu = self.table.createStandardContextMenu()

        if is_favorite:
            # 添加分隔符
            menu.addSeparator()
            # 添加取消收藏动作
            unfavorite_action = menu.addAction("取消收藏")
            unfavorite_action.triggered.connect(lambda: self.unfavorite_requested.emit(train_no_clean))

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _on_double_click(self, index):
        """处理双击事件"""
        row = index.row()
        train_no_item = self.table.item(row, 0)
        if train_no_item:
            # 获取车次号（去除"复"、"智"标识和空格）
            train_no_raw = train_no_item.text().strip()
            train_no = train_no_raw.split()[0]
            # 去除颜色标记
            train_no = train_no.replace('\033[92m', '').replace('\033[93m', '').replace('\033[90m', '').replace('\033[0m', '')
            self.ticket_double_clicked.emit(train_no)

    def set_data(self, tickets: List[Dict], favorites: List[str] = None):
        """
        设置表格数据
        :param tickets: 车票数据列表（解析后的结构化数据）
        :param favorites: 收藏车次列表
        """
        if favorites is None:
            favorites = []

        self.favorites = favorites  # 保存收藏列表用于右键菜单

        # 保存原始数据用于排序和筛选
        # 排序：收藏车次优先
        self.current_data = sorted(tickets, key=lambda x: (x['train_no'].upper() not in [f.upper() for f in favorites], x['departure_time']))
        self.filtered_data = self.current_data.copy()

        # 重置排序状态
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder

        # 刷新表格显示
        self._refresh_table()

    def _apply_row_color(self, row: int, has_ticket: bool, is_favorite: bool):
        """
        应用行颜色
        :param row: 行号
        :param has_ticket: 是否有票
        :param is_favorite: 是否收藏
        """
        # 优先级：收藏 > 有票 > 默认
        if is_favorite:
            color = QColor(255, 255, 200)  # 黄色（收藏优先）
        elif has_ticket:
            color = QColor(200, 255, 200)  # 绿色
        else:
            color = QColor(240, 240, 240)  # 灰色

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(color)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, query_service, config_manager, favorite_service, cache_service,
                 station_search_service, monitor_manager, logger=None):
        super().__init__()
        self.query_service = query_service
        self.config_manager = config_manager
        self.favorite_service = favorite_service
        self.cache_service = cache_service
        self.station_search = station_search_service
        self.monitor_manager = monitor_manager
        self.logger = logger

        self.monitor_timer = None
        self.current_monitor_task_id = None
        self.monitor_interval = 30  # 秒
        self._has_queried = False  # 是否已执行过查询

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("12306 车票查询与监控助手 v3.1.0")

        # 窗口大小自适应屏幕（使用屏幕的 85%）
        screen = QApplication.primaryScreen().availableGeometry()
        window_width = int(screen.width() * 0.85)
        window_height = int(screen.height() * 0.85)
        self.resize(window_width, window_height)
        # 居中显示
        self.move((screen.width() - window_width) // 2, (screen.height() - window_height) // 2)

        # 创建中央 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 创建菜单栏
        self._create_menubar()

        # 输入区域
        input_group = self._create_input_section()
        main_layout.addWidget(input_group)

        # 按钮区域
        button_group = self._create_button_section()
        main_layout.addWidget(button_group)

        # 结果区域（使用分割布局，左侧结果，右侧筛选）
        result_layout = QHBoxLayout()

        # 结果区域
        result_group = self._create_result_section()
        result_layout.addWidget(result_group, stretch=3)

        # 筛选面板
        filter_group = self._create_filter_section()
        result_layout.addWidget(filter_group, stretch=1)

        main_layout.addLayout(result_layout)

        # 状态栏
        self.statusBar().showMessage("就绪")

    def _create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")
        export_action = QAction("导出结果", self)
        export_action.triggered.connect(self._export_results)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 查询菜单
        query_menu = menubar.addMenu("查询")
        history_action = QAction("历史查询", self)
        history_action.triggered.connect(self._show_history_dialog)
        query_menu.addAction(history_action)

        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        fav_action = QAction("管理收藏", self)
        fav_action.triggered.connect(self._show_favorites_dialog)
        edit_menu.addAction(fav_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        interval_action = QAction("监控间隔", self)
        interval_action.triggered.connect(self._set_monitor_interval)
        settings_menu.addAction(interval_action)
        notif_action = QAction("通知设置", self)
        notif_action.triggered.connect(self._show_notification_settings)
        settings_menu.addAction(notif_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_input_section(self) -> QGroupBox:
        """创建输入区域"""
        group = QGroupBox("查询条件")
        layout = QGridLayout(group)

        # 出发站
        layout.addWidget(QLabel("出发站:"), 0, 0)
        self.from_station_input = QLineEdit()
        self.from_station_input.setPlaceholderText("输入站名或拼音")
        self.from_station_input.textChanged.connect(self._on_from_station_changed)
        layout.addWidget(self.from_station_input, 0, 1)

        # 出发站选择按钮
        self.from_station_btn = QPushButton("选择")
        self.from_station_btn.setMaximumWidth(50)
        self.from_station_btn.clicked.connect(lambda: self._show_station_selector(self.from_station_input))
        layout.addWidget(self.from_station_btn, 0, 2)

        # 到达站
        layout.addWidget(QLabel("到达站:"), 0, 3)
        self.to_station_input = QLineEdit()
        self.to_station_input.setPlaceholderText("输入站名或拼音")
        self.to_station_input.textChanged.connect(self._on_to_station_changed)
        layout.addWidget(self.to_station_input, 0, 4)

        # 到达站选择按钮
        self.to_station_btn = QPushButton("选择")
        self.to_station_btn.setMaximumWidth(50)
        self.to_station_btn.clicked.connect(lambda: self._show_station_selector(self.to_station_input))
        layout.addWidget(self.to_station_btn, 0, 5)

        # 日期
        layout.addWidget(QLabel("日期:"), 0, 6)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setMinimumDate(QDate.currentDate())
        self.date_picker.setMaximumDate(QDate.currentDate().addDays(15))
        layout.addWidget(self.date_picker, 0, 7)

        # 打开 12306 按钮（替代车次号栏）
        self.open_12306_button_inline = QPushButton("打开 12306")
        self.open_12306_button_inline.clicked.connect(self._open_12306)
        layout.addWidget(self.open_12306_button_inline, 1, 0, 1, 2)

        # 重置按钮
        self.reset_button = QPushButton("重置查询与筛选")
        self.reset_button.clicked.connect(self._reset_filters)
        layout.addWidget(self.reset_button, 1, 2, 1, 6)

        # 车站补全列表（隐藏，用于自动补全）
        self.from_station_suggestions = QComboBox()
        self.from_station_suggestions.setMaximumHeight(30)
        self.from_station_suggestions.setVisible(False)
        layout.addWidget(self.from_station_suggestions, 0, 1, 1, 1)

        self.to_station_suggestions = QComboBox()
        self.to_station_suggestions.setMaximumHeight(30)
        self.to_station_suggestions.setVisible(False)
        layout.addWidget(self.to_station_suggestions, 0, 4, 1, 1)

        return group

    def _create_filter_section(self) -> QGroupBox:
        """创建筛选面板区域"""
        group = QGroupBox("筛选")
        layout = QVBoxLayout(group)

        # 创建筛选面板
        station_dict = self.station_search.station_dict if self.station_search else {}
        self.filter_panel = FilterPanel(station_dict)
        self.filter_panel.filter_changed.connect(self._on_filter_changed)
        layout.addWidget(self.filter_panel)

        return group

    def _create_button_section(self) -> QWidget:
        """创建按钮区域"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 10, 0, 10)

        # 查询按钮
        self.query_button = QPushButton("查询")
        self.query_button.setMinimumHeight(40)
        self.query_button.clicked.connect(self._do_query)
        layout.addWidget(self.query_button)

        # 开始监控按钮
        self.start_monitor_button = QPushButton("开始监控")
        self.start_monitor_button.setMinimumHeight(40)
        self.start_monitor_button.clicked.connect(self._start_monitoring)
        layout.addWidget(self.start_monitor_button)

        # 停止监控按钮
        self.stop_monitor_button = QPushButton("停止监控")
        self.stop_monitor_button.setMinimumHeight(40)
        self.stop_monitor_button.clicked.connect(self._stop_monitoring)
        self.stop_monitor_button.setEnabled(False)
        layout.addWidget(self.stop_monitor_button)

        # 收藏当前车次按钮
        self.toggle_favorite_button = QPushButton("收藏选中车次")
        self.toggle_favorite_button.setMinimumHeight(40)
        self.toggle_favorite_button.clicked.connect(self._toggle_favorite)
        layout.addWidget(self.toggle_favorite_button)

        return widget

    def _create_result_section(self) -> QGroupBox:
        """创建结果区域"""
        group = QGroupBox("查询结果")
        layout = QVBoxLayout(group)

        # 状态标签和筛选结果统计
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)

        # 状态标签
        self.status_label = QLabel("等待查询...")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)

        # 筛选结果统计标签
        self.filter_result_label = QLabel("未筛选")
        self.filter_result_label.setStyleSheet("color: #666666; font-size: 12px; margin-left: 20px;")
        status_layout.addWidget(self.filter_result_label)

        status_layout.addStretch()
        layout.addWidget(status_widget)

        # 结果表格
        self.result_widget = QueryResultWidget()
        self.result_widget.ticket_double_clicked.connect(self._on_ticket_double_click)
        self.result_widget.unfavorite_requested.connect(self._on_unfavorite_request)
        layout.addWidget(self.result_widget)

        return group

    def _on_from_station_changed(self, text):
        """出发站输入变化"""
        if len(text) >= 1 and self.station_search:
            suggestions = self.station_search.search_station(text)
            self._show_suggestions(self.from_station_suggestions, suggestions, self.from_station_input)
        else:
            self.from_station_suggestions.setVisible(False)

    def _on_to_station_changed(self, text):
        """到达站输入变化"""
        if len(text) >= 1 and self.station_search:
            suggestions = self.station_search.search_station(text)
            self._show_suggestions(self.to_station_suggestions, suggestions, self.to_station_input)
        else:
            self.to_station_suggestions.setVisible(False)

    def _show_suggestions(self, combo: QComboBox, suggestions: List[str], input_widget: QLineEdit):
        """显示建议列表"""
        if not suggestions:
            combo.setVisible(False)
            return

        # 断开旧的连接，避免重复触发
        try:
            combo.currentTextChanged.disconnect()
        except (TypeError, RuntimeError):
            pass  # 没有连接时忽略

        combo.clear()
        combo.addItems(suggestions)
        combo.setVisible(True)
        combo.setMaxVisibleItems(10)

        # 点击建议时填充输入框
        combo.currentTextChanged.connect(lambda t: self._select_suggestion(t, combo, input_widget))

    def _select_suggestion(self, text, combo: QComboBox, input_widget: QLineEdit):
        """选择建议"""
        # 阻止信号触发，避免再次触发 textChanged
        input_widget.blockSignals(True)
        input_widget.setText(text)
        input_widget.blockSignals(False)
        combo.setVisible(False)
        # 隐藏后断开连接，避免后续干扰
        try:
            combo.currentTextChanged.disconnect()
        except (TypeError, RuntimeError):
            pass

    def _show_station_selector(self, target_input: QLineEdit):
        """显示车站选择器对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择车站")
        dialog.setMinimumSize(500, 400)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # 提示标签
        hint_label = QLabel("请选择车站：")
        layout.addWidget(hint_label)

        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("搜索:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("输入站名或拼音首字母")
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input)
        layout.addLayout(search_layout)

        # 车站列表
        station_list = QListWidget()
        station_list.setAlternatingRowColors(True)

        # 根据目标输入框确定是出发站还是到达站，并过滤车站
        is_from_station = (target_input == self.from_station_input)
        city_name = target_input.text().strip()

        # 获取车站列表（根据城市名过滤）
        def populate_station_list(city=None):
            station_list.clear()
            if self.station_search:
                if city:
                    # 按城市过滤
                    stations = self.station_search.get_stations_by_city(city)
                else:
                    # 显示所有车站
                    stations = sorted(self.station_search.station_dict.keys())[:500]
                for station in stations:
                    station_list.addItem(station)

        # 初始加载
        populate_station_list(city_name if city_name else None)

        layout.addWidget(station_list)

        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 双击选择
        def on_item_double_click(item):
            target_input.setText(item.text())
            dialog.accept()

        station_list.itemDoubleClicked.connect(on_item_double_click)

        # 搜索功能
        def on_search_text_changed(text):
            station_list.clear()
            if not text:
                # 显示所有车站或当前城市车站
                populate_station_list(city_name if city_name else None)
            else:
                # 搜索匹配的车站
                if self.station_search:
                    suggestions = self.station_search.search_station(text)
                    for station in suggestions:
                        station_list.addItem(station)

        search_input.textChanged.connect(on_search_text_changed)

        # 按钮事件
        ok_button.clicked.connect(lambda: self._confirm_station_selection(station_list, target_input, dialog))
        cancel_button.clicked.connect(dialog.reject)

        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            pass  # 已经在双击时设置了

    def _confirm_station_selection(self, station_list: QListWidget, target_input: QLineEdit, dialog: QDialog):
        """确认车站选择"""
        current_item = station_list.currentItem()
        if current_item:
            target_input.setText(current_item.text())
            dialog.accept()

    def _reset_filters(self):
        """重置所有查询和筛选条件"""
        # 清空输入
        self.from_station_input.clear()
        self.to_station_input.clear()
        self.date_picker.setDate(QDate.currentDate())

        # 重置筛选面板
        if hasattr(self, 'filter_panel'):
            self.filter_panel.reset_filters()

        # 清空结果表格
        self.result_widget.set_data([], [])
        self._has_queried = False

        # 重置筛选统计
        self.filter_result_label.setText("未筛选")

        # 重置状态
        self.status_label.setText("等待查询...")
        self.statusBar().showMessage("已重置查询条件")

    def _on_filter_changed(self):
        """筛选条件变化，实时过滤"""
        filter_config = self.filter_panel.get_filter_config()
        self.result_widget.apply_filters(filter_config)

        # 更新筛选结果统计
        if hasattr(self, 'filter_result_label'):
            total_count = len(self.result_widget.current_data)
            filtered_count = len(self.result_widget.filtered_data)

            # 检查是否有活跃的筛选条件
            has_active_filter = False
            train_types = filter_config.get('train_types', [])
            if train_types and len(train_types) < len(['GC', 'D', 'Z', 'T', 'K', '其他']):
                has_active_filter = True

            from_stations = filter_config.get('from_stations', [])
            if from_stations and len(from_stations) < len(filter_config.get('all_from_stations', [])):
                has_active_filter = True

            to_stations = filter_config.get('to_stations', [])
            if to_stations and len(to_stations) < len(filter_config.get('all_to_stations', [])):
                has_active_filter = True

            seat_types = filter_config.get('seat_types', [])
            if seat_types and len(seat_types) < len(['business', 'first', 'second', 'soft_sleeper', 'hard_sleeper', 'soft_seat', 'hard_seat', 'no_seat']):
                has_active_filter = True

            time_period = filter_config.get('time_period', '00:00-24:00')
            if time_period != '00:00-24:00':
                has_active_filter = True

            show_fuxing = filter_config.get('show_fuxing', True)
            if not show_fuxing:
                has_active_filter = True

            show_smart = filter_config.get('show_smart', True)
            if not show_smart:
                has_active_filter = True

            if has_active_filter:
                self.filter_result_label.setText(f"筛选结果：{filtered_count} / {total_count} 趟")
            else:
                self.filter_result_label.setText("未筛选")

    def _do_query(self, monitoring: bool = False):
        """执行查询"""
        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not from_station or not to_station:
            QMessageBox.warning(self, "警告", "请输入出发站和到达站")
            return

        # 查询历史已由 logger/query_history.py 自动记录，此处无需额外保存

        # 解析车次筛选（已移除，预留接口）
        target_trains = None

        self.status_label.setText(f"正在查询：{from_station} -> {to_station} ({date}) ...")
        self.statusBar().showMessage("查询中...")
        QApplication.processEvents()

        try:
            # 执行查询
            result = self.query_service.execute_query(
                date=date,
                from_station=from_station,
                to_station=to_station,
                target_trains=target_trains,
                filters=None,  # 不再使用原来的席别筛选
                quick_mode=not monitoring
            )

            if result.get("error"):
                if result["error"] == "STATION_NOT_FOUND":
                    QMessageBox.warning(self, "错误", "站名不存在，请检查输入")
                else:
                    QMessageBox.warning(self, "错误", "查询失败，请稍后重试")
                return

            # 获取收藏列表
            favorites = self.favorite_service.get_favorites()

            # 转换结果为结构化数据（添加车次类型和标识）
            tickets_data = self._convert_tickets_to_data(result.get("all_tickets", []))

            # 获取出发城市和到达城市的所有车站（同城车站列表）
            from_stations = []
            to_stations = []
            if self.station_search:
                from_stations = self.station_search.get_stations_by_city(from_station)
                to_stations = self.station_search.get_stations_by_city(to_station)

            # 更新筛选面板的车站列表
            if hasattr(self, 'filter_panel'):
                self.filter_panel.update_stations(from_stations=from_stations, to_stations=to_stations)

            # 显示结果
            self.result_widget.set_data(tickets_data, favorites)
            self._has_queried = True

            # 同步更新筛选统计
            self._on_filter_changed()

            # 根据模式显示不同信息
            if monitoring:
                total = result.get("total_count", 0)
                available = result.get("available_count", 0)
                self.status_label.setText(f"监控中：{from_station} -> {to_station} ({date}) | 共 {total} 车次 | 有票 {available} 车次")
                self.statusBar().showMessage(f"监控运行中 - {total}车次 / {available}有票")
            else:
                total = result.get("total_count", 0)
                self.status_label.setText(f"查询完成：{from_station} -> {to_station} ({date}) | 共 {total} 车次")
                self.statusBar().showMessage(f"查询完成 - 共{total}车次")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败：{e}")
            self.logger.error(f"GUI 查询失败：{e}", exc_info=True) if self.logger else print(f"错误：{e}")

    def _convert_tickets_to_data(self, tickets) -> List[Dict]:
        """
        转换 TicketInfo 列表为结构化字典列表（添加车次类型和标识）
        :param tickets: TicketInfo 列表
        :return: 字典列表
        """
        result = []
        for ticket in tickets:
            train_no = ticket.train_no
            train_type = TrainClassifier.classify_train(train_no)
            is_fuxing = TrainClassifier.is_fuxing(train_no)
            is_smart = TrainClassifier.is_smart(train_no)

            data = {
                'train_no': train_no,
                'train_type': train_type,
                'is_fuxing': is_fuxing,
                'is_smart': is_smart,
                'from_station': ticket.from_station,
                'to_station': ticket.to_station,
                'departure_time': ticket.departure_time,
                'arrival_time': getattr(ticket, 'arrival_time', '--'),
                'duration': ticket.duration,
                'has_ticket': bool(ticket.available_seats),
                'business_seat': ticket.available_seats.get('商/特', '--'),
                'first_seat': ticket.available_seats.get('一等座', '--'),
                'second_seat': ticket.available_seats.get('二等座', '--'),
                'soft_sleeper': ticket.available_seats.get('一等/软卧', '--'),
                'hard_sleeper': ticket.available_seats.get('二等/硬卧', '--'),
                'soft_seat': ticket.available_seats.get('软座', '--'),
                'hard_seat': ticket.available_seats.get('硬座', '--'),
                'no_seat': ticket.available_seats.get('无座', '--'),
            }
            result.append(data)
        return result

    def _start_monitoring(self):
        """开始监控"""
        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not from_station or not to_station:
            QMessageBox.warning(self, "警告", "请先输入查询条件")
            return

        # 创建监控任务
        task_id = self.monitor_manager.create_task(
            from_station=from_station,
            to_station=to_station,
            date=date,
            target_trains=None,
            interval_seconds=self.monitor_interval
        )

        # 启动监控
        self.monitor_manager.start_task(task_id, callback=self._on_monitor_tick)
        self.current_monitor_task_id = task_id

        # 更新 UI
        self.start_monitor_button.setEnabled(False)
        self.stop_monitor_button.setEnabled(True)
        self.query_button.setEnabled(False)

        self.status_label.setText(f"监控中：{from_station} -> {to_station} | 间隔 {self.monitor_interval}秒")
        self.statusBar().showMessage(f"监控运行中...")

        self._do_query(monitoring=True)

    def _stop_monitoring(self):
        """停止监控"""
        if self.current_monitor_task_id:
            self.monitor_manager.stop_task(self.current_monitor_task_id)
            self.current_monitor_task_id = None

        # 更新 UI
        self.start_monitor_button.setEnabled(True)
        self.stop_monitor_button.setEnabled(False)
        self.query_button.setEnabled(True)

        self.status_label.setText("监控已停止")
        self.statusBar().showMessage("监控已停止")

    def _on_monitor_tick(self):
        """监控定时器回调"""
        self._do_query(monitoring=True)

    def _toggle_favorite(self):
        """切换收藏状态"""
        selected_rows = self.result_widget.table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要收藏的车次")
            return

        # 获取选中的车次
        row = selected_rows[0].row()
        train_no_item = self.result_widget.table.item(row, 0)
        if not train_no_item:
            return

        train_no = train_no_item.text().strip().split()[0]  # 去除"复"、"智"标识

        # 切换收藏状态
        is_favorite = self.favorite_service.toggle_favorite(train_no)

        if is_favorite:
            self.statusBar().showMessage(f"已收藏：{train_no}")
        else:
            self.statusBar().showMessage(f"已取消收藏：{train_no}")

        # 刷新显示
        self._do_query()

    def _on_unfavorite_request(self, train_no):
        """处理右键取消收藏请求"""
        # 取消收藏
        is_favorite = self.favorite_service.toggle_favorite(train_no)

        if not is_favorite:
            self.statusBar().showMessage(f"已取消收藏：{train_no}")
        else:
            self.statusBar().showMessage(f"已收藏：{train_no}")

        # 刷新显示
        self._do_query()

    def _show_favorites_dialog(self):
        """显示收藏管理对话框"""
        favorites = self.favorite_service.get_favorites()

        dialog = QDialog(self)
        dialog.setWindowTitle("管理收藏")
        dialog.setMinimumSize(400, 300)

        layout = QVBoxLayout(dialog)

        # 收藏列表
        favorites_list = QTableWidget()
        favorites_list.setColumnCount(1)
        favorites_list.setHorizontalHeaderLabels(["收藏车次"])
        favorites_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for fav in favorites:
            row = favorites_list.rowCount()
            favorites_list.insertRow(row)
            favorites_list.setItem(row, 0, QTableWidgetItem(fav))

        layout.addWidget(QLabel("已收藏的车次："))
        layout.addWidget(favorites_list)

        # 删除按钮
        delete_button = QPushButton("删除选中")
        delete_button.clicked.connect(lambda: self._delete_selected_favorites(favorites_list))
        layout.addWidget(delete_button)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)

        dialog.exec()

    def _delete_selected_favorites(self, table: QTableWidget):
        """删除选中的收藏"""
        selected_rows = table.selectedItems()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先选择要删除的车次")
            return

        for item in selected_rows:
            train_no = item.text()
            self.favorite_service.remove_favorite(train_no)
            table.removeRow(item.row())

    def _export_results(self):
        """导出结果"""
        current_rows = self.result_widget.table.rowCount()
        if current_rows == 0:
            QMessageBox.information(self, "提示", "没有可导出的数据")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出结果", "", "JSON 文件 (*.json);;CSV 文件 (*.csv);;所有文件 (*)"
        )

        if file_path:
            try:
                # 简化导出：直接导出当前表格数据
                data = []
                for row in range(current_rows):
                    row_data = {}
                    for col in range(self.result_widget.table.columnCount()):
                        item = self.result_widget.table.item(row, col)
                        if item:
                            header = self.result_widget.table.horizontalHeaderItem(col).text()
                            row_data[header] = item.text()
                    data.append(row_data)

                import json
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                QMessageBox.information(self, "成功", f"已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败：{e}")

    def _set_monitor_interval(self):
        """设置监控间隔"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置监控间隔")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("监控查询间隔（秒）:"))

        spinbox = QSpinBox()
        spinbox.setMinimum(10)
        spinbox.setMaximum(300)
        spinbox.setValue(self.monitor_interval)
        layout.addWidget(spinbox)

        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        if dialog.exec() == QDialog.Accepted:
            self.monitor_interval = spinbox.value()
            self.statusBar().showMessage(f"监控间隔已设置为 {self.monitor_interval}秒")

            # 更新当前任务
            if self.current_monitor_task_id:
                self.monitor_manager.update_task_interval(self.current_monitor_task_id, self.monitor_interval)

    def _show_notification_settings(self):
        """显示通知设置对话框"""
        config = self.config_manager.get_config()
        notif_config = config.setdefault("notification", {})
        channels = notif_config.setdefault("channels", {})

        dialog = QDialog(self)
        dialog.setWindowTitle("通知设置")
        dialog.setMinimumSize(500, 400)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # 全局开关
        global_enabled_cb = QCheckBox("启用通知")
        global_enabled_cb.setChecked(notif_config.get("enabled", True))
        layout.addWidget(global_enabled_cb)

        # 冷却时间
        cooldown_layout = QHBoxLayout()
        cooldown_layout.addWidget(QLabel("通知冷却时间（秒）:"))
        cooldown_spin = QSpinBox()
        cooldown_spin.setMinimum(10)
        cooldown_spin.setMaximum(3600)
        cooldown_spin.setValue(notif_config.get("cooldown_seconds", 300))
        cooldown_layout.addWidget(cooldown_spin)
        layout.addLayout(cooldown_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # --- Windows 原生通知 ---
        win_group = QGroupBox("Windows 原生通知")
        win_layout = QVBoxLayout(win_group)
        win_enabled_cb = QCheckBox("启用（使用系统 Toast 通知，无需额外配置）")
        win_enabled_cb.setChecked(channels.get("windows_desktop", {}).get("enabled", True))
        win_layout.addWidget(win_enabled_cb)
        layout.addWidget(win_group)

        # --- 企业微信 ---
        wx_group = QGroupBox("企业微信机器人")
        wx_layout = QVBoxLayout(wx_group)
        wx_enabled_cb = QCheckBox("启用")
        wx_enabled_cb.setChecked(channels.get("wechat_work", {}).get("enabled", False))
        wx_layout.addWidget(wx_enabled_cb)
        wx_url_layout = QHBoxLayout()
        wx_url_layout.addWidget(QLabel("Webhook URL:"))
        wx_url_input = QLineEdit()
        wx_url_input.setPlaceholderText("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...")
        wx_url_input.setText(channels.get("wechat_work", {}).get("webhook_url", ""))
        wx_url_layout.addWidget(wx_url_input)
        wx_layout.addLayout(wx_url_layout)
        layout.addWidget(wx_group)

        # --- 飞书 ---
        feishu_group = QGroupBox("飞书机器人")
        feishu_layout = QVBoxLayout(feishu_group)
        feishu_enabled_cb = QCheckBox("启用")
        feishu_enabled_cb.setChecked(channels.get("feishu", {}).get("enabled", False))
        feishu_layout.addWidget(feishu_enabled_cb)
        feishu_url_layout = QHBoxLayout()
        feishu_url_layout.addWidget(QLabel("Webhook URL:"))
        feishu_url_input = QLineEdit()
        feishu_url_input.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/...")
        feishu_url_input.setText(channels.get("feishu", {}).get("webhook_url", ""))
        feishu_url_layout.addWidget(feishu_url_input)
        feishu_layout.addLayout(feishu_url_layout)
        layout.addWidget(feishu_group)

        # --- 钉钉 ---
        ding_group = QGroupBox("钉钉机器人")
        ding_layout = QVBoxLayout(ding_group)
        ding_enabled_cb = QCheckBox("启用")
        ding_enabled_cb.setChecked(channels.get("dingtalk", {}).get("enabled", False))
        ding_layout.addWidget(ding_enabled_cb)
        ding_url_layout = QHBoxLayout()
        ding_url_layout.addWidget(QLabel("Webhook URL:"))
        ding_url_input = QLineEdit()
        ding_url_input.setPlaceholderText("https://oapi.dingtalk.com/robot/send?access_token=...")
        ding_url_input.setText(channels.get("dingtalk", {}).get("webhook_url", ""))
        ding_url_layout.addWidget(ding_url_input)
        ding_layout.addLayout(ding_url_layout)
        ding_secret_layout = QHBoxLayout()
        ding_secret_layout.addWidget(QLabel("签名密钥:"))
        ding_secret_input = QLineEdit()
        ding_secret_input.setPlaceholderText("SEC...（可选，用于加签）")
        ding_secret_input.setText(channels.get("dingtalk", {}).get("secret", ""))
        ding_secret_layout.addWidget(ding_secret_input)
        ding_layout.addLayout(ding_secret_layout)
        layout.addWidget(ding_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_button = QPushButton("保存")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        def on_save():
            notif_config["enabled"] = global_enabled_cb.isChecked()
            notif_config["cooldown_seconds"] = cooldown_spin.value()

            channels["windows_desktop"] = {"enabled": win_enabled_cb.isChecked()}
            channels["wechat_work"] = {
                "enabled": wx_enabled_cb.isChecked(),
                "webhook_url": wx_url_input.text().strip()
            }
            channels["feishu"] = {
                "enabled": feishu_enabled_cb.isChecked(),
                "webhook_url": feishu_url_input.text().strip()
            }
            channels["dingtalk"] = {
                "enabled": ding_enabled_cb.isChecked(),
                "webhook_url": ding_url_input.text().strip(),
                "secret": ding_secret_input.text().strip()
            }

            self.config_manager.save_config()
            self.statusBar().showMessage("通知设置已保存")
            dialog.accept()

        save_button.clicked.connect(on_save)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def _open_12306(self):
        """打开 12306 网页"""
        import webbrowser

        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not self._has_queried or not from_station or not to_station:
            # 未执行查询时，打开 12306 首页
            webbrowser.open("https://www.12306.cn")
        else:
            # 已执行查询时，打开对应路线的查询界面
            from_code = self.query_service.ticket_api.get_station_code(from_station)
            to_code = self.query_service.ticket_api.get_station_code(to_station)

            if from_code and to_code:
                url = f"https://kyfw.12306.cn/otn/leftTicket/init?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
                webbrowser.open(url)
            else:
                webbrowser.open("https://www.12306.cn")

    def _on_ticket_double_click(self, train_no):
        """处理车次双击"""
        # 双击时自动收藏/取消收藏
        is_favorite = self.favorite_service.toggle_favorite(train_no)
        if is_favorite:
            self.statusBar().showMessage(f"已收藏：{train_no}")
        else:
            self.statusBar().showMessage(f"已取消收藏：{train_no}")
        self._do_query()

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于",
            "12306 车票查询与监控助手 v3.1.0\n\n"
            "基于 PySide6 的 GUI 版本\n\n"
            "功能特性:\n"
            "- 余票查询\n"
            "- 自动监控\n"
            "- 车次收藏\n"
            "- 查询缓存\n"
            "- 车站自动补全\n"
            "- 结果高亮显示\n"
            "- 多任务监控\n"
            "- 手动打开 12306\n"
            "- 高级筛选（车次类型/车站/席别/时段）\n"
            "- 复兴号/智能动车组标识 \n\n"
            "开发：BH7GUL"
        )

    def _show_history_dialog(self):
        """显示历史查询对话框"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QMessageBox

        dialog = QDialog(self)
        dialog.setWindowTitle("查询历史")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout(dialog)

        # 历史记录列表（支持多选）
        history_list = QListWidget()
        history_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(history_list)

        # 按钮区域
        button_layout = QHBoxLayout()

        requery_button = QPushButton("重新查询")
        requery_button.setEnabled(False)
        button_layout.addWidget(requery_button)

        delete_button = QPushButton("删除选中")
        delete_button.setEnabled(False)
        button_layout.addWidget(delete_button)

        clear_button = QPushButton("清空全部")
        button_layout.addWidget(clear_button)

        close_button = QPushButton("关闭")
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # 加载历史记录
        recent_history = self.query_service.query_history.get_recent(50)

        def refresh_list():
            """刷新列表显示"""
            nonlocal recent_history
            recent_history = self.query_service.query_history.get_recent(50)
            history_list.clear()
            for record in reversed(recent_history):
                timestamp = record.get('timestamp', '').split('T')[0]
                from_station = record.get('from', '')
                to_station = record.get('to', '')
                date = record.get('date', '')
                total_count = record.get('total_count', 0)
                available_count = record.get('available_count', 0)

                item_text = f"{timestamp} {from_station} → {to_station} ({date}) - 共{total_count}车，有票{available_count}车"
                history_list.addItem(item_text)

        refresh_list()

        # 选择事件
        def on_selection_changed():
            selected = history_list.currentRow() != -1
            requery_button.setEnabled(selected)
            delete_button.setEnabled(selected)

        history_list.currentRowChanged.connect(on_selection_changed)

        # 重新查询
        def on_requery():
            selected_row = history_list.currentRow()
            if selected_row >= 0:
                record = recent_history[-(selected_row + 1)]
                self.from_station_input.setText(record.get('from', ''))
                self.to_station_input.setText(record.get('to', ''))

                date_obj = QDate.fromString(record.get('date', ''), "yyyy-MM-dd")
                if date_obj.isValid():
                    self.date_picker.setDate(date_obj)

                self._do_query()
                dialog.accept()

        requery_button.clicked.connect(on_requery)

        # 删除选中记录
        def on_delete():
            selected_rows = sorted(set(item.row() for item in history_list.selectedItems()), reverse=True)
            if not selected_rows:
                return

            reply = QMessageBox.question(
                dialog, "确认删除",
                f"确定要删除选中的 {len(selected_rows)} 条记录吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            # 将列表行号转为 history 索引（列表是倒序显示的）
            indices = [history_list.count() - 1 - row for row in selected_rows]
            self.query_service.query_history.delete_by_index(indices)

            refresh_list()
            self.statusBar().showMessage(f"已删除 {len(indices)} 条历史记录")

        delete_button.clicked.connect(on_delete)

        # 清空全部记录
        def on_clear():
            if history_list.count() == 0:
                return

            reply = QMessageBox.question(
                dialog, "确认清空",
                "确定要清空全部查询历史吗？此操作不可恢复。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

            self.query_service.query_history.delete_by_index(list(range(history_list.count())))
            refresh_list()
            self.statusBar().showMessage("已清空全部历史记录")

        clear_button.clicked.connect(on_clear)

        # 关闭
        close_button.clicked.connect(dialog.accept)

        dialog.exec()

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止所有监控任务
        self.monitor_manager.stop_all_tasks()
        event.accept()


# 导入 QDialog（如果上面使用了）
from PySide6.QtWidgets import QDialog
