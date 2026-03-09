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
    QHeaderView, QMessageBox, QFileDialog, QGroupBox, QSpinBox, QComboBox,
    QTextEdit, QFrame, QTabWidget, QMenuBar, QMenu, QApplication, QListWidget,
    QDialog
)
from PySide6.QtCore import Qt, QTimer, QDate, Signal
from PySide6.QtGui import QColor, QFont, QAction


class QueryResultWidget(QWidget):
    """查询结果表格组件"""

    ticket_double_clicked = Signal(str)  # 车次号（双击时触发）
    unfavorite_requested = Signal(str)  # 取消收藏请求（右键菜单触发）

    def __init__(self):
        super().__init__()
        self.favorites = []  # 当前收藏列表
        self.current_data = []  # 当前表格数据（用于排序）
        self.sort_column = -1  # 当前排序列
        self.sort_order = Qt.AscendingOrder  # 当前排序顺序
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            "车次", "始发站", "到达站", "开点", "到点", "历时",
            "商务座/特等座", "一等座", "二等座", "软卧/动卧/一等卧", "硬卧/二等卧", "软座", "硬座", "无座"
        ])

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 车次
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 始发站
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 到达站
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 开点
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # 到点
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 历时
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 商/特
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # 一等座
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # 二等座
        header.setSectionResizeMode(9, QHeaderView.Stretch)  # 软卧/动卧/一等卧
        header.setSectionResizeMode(10, QHeaderView.Stretch)  # 硬卧/二等卧
        header.setSectionResizeMode(11, QHeaderView.Stretch)  # 软座

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
        # logical_index: 0=车次，1=始发站，2=到达站，3=开点，4=到点，5=历时
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

        # 刷新表格显示
        self._refresh_table()

    def _refresh_table(self):
        """刷新表格显示（不改变数据）"""
        self.table.setRowCount(0)

        for ticket in self.current_data:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            train_no = ticket['train_no']
            has_ticket = ticket.get('has_ticket', False)
            is_favorite = train_no.upper() in [f.upper() for f in self.favorites]

            # 设置数据
            self.table.setItem(row_position, 0, QTableWidgetItem(train_no))
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

        train_no = train_no_item.text().strip()
        # 去除颜色标记
        train_no_clean = train_no.replace('\033[92m', '').replace('\033[93m', '').replace('\033[90m', '').replace('\033[0m', '')

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
            train_no = train_no_item.text().strip()
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

        # 保存原始数据用于排序
        # 排序：收藏车次优先
        self.current_data = sorted(tickets, key=lambda x: (x['train_no'].upper() not in [f.upper() for f in favorites], x['departure_time']))

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
        if has_ticket:
            color = QColor(200, 255, 200)  # 绿色
        elif is_favorite:
            color = QColor(255, 255, 200)  # 黄色
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

        # 查询历史栈（用于回退功能）
        self.query_history_stack = []
        self.max_history = 10  # 最多保存 10 条历史记录

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("12306 余票监控工具 v3.0.0")
        self.setMinimumSize(1200, 800)

        # 创建中央 widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建菜单栏
        self._create_menubar()

        # 输入区域
        input_group = self._create_input_section()
        main_layout.addWidget(input_group)

        # 按钮区域
        button_group = self._create_button_section()
        main_layout.addWidget(button_group)

        # 结果区域
        result_group = self._create_result_section()
        main_layout.addWidget(result_group)

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
        self.from_station_input.setPlaceholderText("例如：北京（支持拼音首字母）")
        self.from_station_input.textChanged.connect(self._on_from_station_changed)
        layout.addWidget(self.from_station_input, 0, 1)

        # 出发站选择按钮
        self.from_station_btn = QPushButton("选择")
        self.from_station_btn.setMaximumWidth(50)
        self.from_station_btn.clicked.connect(lambda: self._show_station_selector(self.from_station_input))
        layout.addWidget(self.from_station_btn, 0, 1, 1, 1, Qt.AlignRight)

        # 到达站
        layout.addWidget(QLabel("到达站:"), 0, 2)
        self.to_station_input = QLineEdit()
        self.to_station_input.setPlaceholderText("例如：上海（支持拼音首字母）")
        self.to_station_input.textChanged.connect(self._on_to_station_changed)
        layout.addWidget(self.to_station_input, 0, 3)

        # 到达站选择按钮
        self.to_station_btn = QPushButton("选择")
        self.to_station_btn.setMaximumWidth(50)
        self.to_station_btn.clicked.connect(lambda: self._show_station_selector(self.to_station_input))
        layout.addWidget(self.to_station_btn, 0, 3, 1, 1, Qt.AlignRight)

        # 日期
        layout.addWidget(QLabel("日期:"), 0, 4)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setMinimumDate(QDate.currentDate())
        self.date_picker.setMaximumDate(QDate.currentDate().addDays(15))
        layout.addWidget(self.date_picker, 0, 5)

        # 车次筛选
        layout.addWidget(QLabel("车次筛选:"), 1, 0)
        self.train_filter_input = QLineEdit()
        self.train_filter_input.setPlaceholderText("例如：G100 G102（空格分隔，留空显示全部）")
        layout.addWidget(self.train_filter_input, 1, 1)

        # 座位筛选
        layout.addWidget(QLabel("座位筛选:"), 1, 2)
        self.seat_filter_combo = QComboBox()
        self.seat_filter_combo.addItems(["全部", "商务座", "一等座", "二等座", "软卧", "硬卧", "无座"])
        layout.addWidget(self.seat_filter_combo, 1, 3)

        # 车站补全列表（隐藏，用于自动补全）
        self.from_station_suggestions = QComboBox()
        self.from_station_suggestions.setMaximumHeight(30)
        self.from_station_suggestions.setVisible(False)
        layout.addWidget(self.from_station_suggestions, 0, 1, 1, 1)

        self.to_station_suggestions = QComboBox()
        self.to_station_suggestions.setMaximumHeight(30)
        self.to_station_suggestions.setVisible(False)
        layout.addWidget(self.to_station_suggestions, 0, 3, 1, 1)

        return group

    def _create_button_section(self) -> QWidget:
        """创建按钮区域"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 10, 0, 10)

        # 回退按钮（初始隐藏）
        self.back_button = QPushButton("返回")
        self.back_button.setMinimumHeight(40)
        self.back_button.clicked.connect(self._do_back)
        self.back_button.setVisible(False)
        layout.addWidget(self.back_button)

        # 查询按钮
        self.query_button = QPushButton("查询")
        self.query_button.setMinimumHeight(40)
        self.query_button.clicked.connect(self._do_query)
        layout.addWidget(self.query_button)

        # 打开 12306 按钮
        self.open_12306_button = QPushButton("打开 12306")
        self.open_12306_button.setMinimumHeight(40)
        self.open_12306_button.clicked.connect(self._open_12306)
        layout.addWidget(self.open_12306_button)

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

        # 状态标签
        self.status_label = QLabel("等待查询...")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.status_label)

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

        # 获取所有车站
        if self.station_search:
            all_stations = sorted(self.station_search.station_dict.keys())
            for station in all_stations[:500]:  # 限制显示数量
                station_list.addItem(station)

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
                # 显示所有车站（限制数量）
                if self.station_search:
                    all_stations = sorted(self.station_search.station_dict.keys())
                    for station in all_stations[:500]:
                        station_list.addItem(station)
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

    def _do_query(self, monitoring: bool = False):
        """执行查询"""
        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not from_station or not to_station:
            QMessageBox.warning(self, "警告", "请输入出发站和到达站")
            return

        # 保存查询历史（仅非监控模式）
        if not monitoring:
            self._save_query_history(from_station, to_station, date)

        # 解析车次筛选
        target_trains = None
        train_filter = self.train_filter_input.text().strip()
        if train_filter:
            target_trains = [t.strip().upper() for t in train_filter.split()]

        # 座位筛选
        seat_filter = self.seat_filter_combo.currentText()
        if seat_filter == "全部":
            seat_filter = None

        self.status_label.setText(f"正在查询：{from_station} -> {to_station} ({date}) ...")
        self.statusBar().showMessage("查询中...")
        QApplication.processEvents()

        try:
            # 执行查询 - 快速模式不统计详细信息，提高响应速度
            # 监控模式下进行完整统计
            result = self.query_service.execute_query(
                date=date,
                from_station=from_station,
                to_station=to_station,
                target_trains=target_trains,
                filters={'type': seat_filter},
                quick_mode=not monitoring  # 非监控模式使用快速模式
            )

            if result.get("error"):
                if result["error"] == "STATION_NOT_FOUND":
                    QMessageBox.warning(self, "错误", "站名不存在，请检查输入")
                else:
                    QMessageBox.warning(self, "错误", "查询失败，请稍后重试")
                return

            # 获取收藏列表
            favorites = self.favorite_service.get_favorites()

            # 转换结果为结构化数据
            tickets_data = self._convert_tickets_to_data(result.get("all_tickets", []))

            # 显示结果
            self.result_widget.set_data(tickets_data, favorites)

            # 根据模式显示不同信息
            if monitoring:
                # 监控模式：显示完整统计信息
                total = result.get("total_count", 0)
                available = result.get("available_count", 0)
                self.status_label.setText(f"监控中：{from_station} -> {to_station} ({date}) | 共 {total} 车次 | 有票 {available} 车次")
                self.statusBar().showMessage(f"监控运行中 - {total}车次 / {available}有票")
            else:
                # 快速模式：只显示基本查询完成信息
                total = result.get("total_count", 0)
                self.status_label.setText(f"查询完成：{from_station} -> {to_station} ({date}) | 共 {total} 车次")
                self.statusBar().showMessage(f"查询完成 - 共{total}车次")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败：{e}")
            self.logger.error(f"GUI 查询失败：{e}", exc_info=True) if self.logger else print(f"错误：{e}")

    def _convert_tickets_to_data(self, tickets) -> List[Dict]:
        """
        转换 TicketInfo 列表为结构化字典列表
        :param tickets: TicketInfo 列表
        :return: 字典列表
        """
        result = []
        for ticket in tickets:
            data = {
                'train_no': ticket.train_no,
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

        self._do_query(monitoring=True)  # 立即查询一次，使用监控模式

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

        train_no = train_no_item.text().strip()

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

    def _open_12306(self):
        """打开 12306 网页"""
        import webbrowser

        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        # 检查是否有查询车次
        current_rows = self.result_widget.table.rowCount()

        if current_rows == 0 or not from_station or not to_station:
            # 没有查询车次时，打开 12306 首页
            webbrowser.open("https://www.12306.cn")
        else:
            # 有查询车次时，打开对应路线的查询界面
            # 需要先获取车站代码
            from_code = self.query_service.ticket_api.get_station_code(from_station)
            to_code = self.query_service.ticket_api.get_station_code(to_station)

            if from_code and to_code:
                url = f"https://kyfw.12306.cn/otn/leftTicket/init?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"
                webbrowser.open(url)
            else:
                # 如果获取不到车站代码，打开首页
                webbrowser.open("https://www.12306.cn")

    def _save_query_history(self, from_station, to_station, date):
        """保存查询历史"""
        # 避免重复保存相同的查询
        if self.query_history_stack:
            last = self.query_history_stack[-1]
            if last['from'] == from_station and last['to'] == to_station and last['date'] == date:
                return

        self.query_history_stack.append({
            'from': from_station,
            'to': to_station,
            'date': date,
            'train_filter': self.train_filter_input.text().strip(),
            'seat_filter': self.seat_filter_combo.currentText()
        })

        # 限制历史数量
        if len(self.query_history_stack) > self.max_history:
            self.query_history_stack.pop(0)

        # 更新返回按钮状态
        self.back_button.setVisible(len(self.query_history_stack) > 1)

    def _do_back(self):
        """回退到上一次查询"""
        if len(self.query_history_stack) <= 1:
            self.back_button.setVisible(False)
            return

        # 弹出当前查询
        self.query_history_stack.pop()

        # 获取上一次查询条件
        if self.query_history_stack:
            last = self.query_history_stack[-1]
            self.from_station_input.setText(last['from'])
            self.to_station_input.setText(last['to'])

            # 设置日期
            date_obj = QDate.fromString(last['date'], "yyyy-MM-dd")
            if date_obj.isValid():
                self.date_picker.setDate(date_obj)

            # 设置筛选条件
            self.train_filter_input.setText(last['train_filter'])
            index = self.seat_filter_combo.findText(last['seat_filter'])
            if index >= 0:
                self.seat_filter_combo.setCurrentIndex(index)

            # 执行查询
            self._do_query()

        # 更新返回按钮状态
        self.back_button.setVisible(len(self.query_history_stack) > 1)

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
            "12306 车票查询与监控助手 v3.0.0\n\n"
            "基于 PySide6 的 GUI 版本\n\n"
            "功能特性:\n"
            "- 余票查询\n"
            "- 自动监控\n"
            "- 车次收藏\n"
            "- 查询缓存\n"
            "- 车站自动补全\n"
            "- 结果高亮显示\n"
            "- 多任务监控\n"
            "- 手动打开 12306"
        )

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止所有监控任务
        self.monitor_manager.stop_all_tasks()
        event.accept()


# 导入 QDialog（如果上面使用了）
from PySide6.QtWidgets import QDialog
