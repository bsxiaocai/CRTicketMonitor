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
    QFrame, QTabWidget, QApplication, QListWidget, QDialog
)
from PySide6.QtCore import Qt, QTimer, QDate, QThreadPool
from PySide6.QtGui import QAction

from ui.gui.filter_panel import FilterPanel
from ui.gui.price_detail_dialog import PriceDetailDialog
from ui.gui.query_result_widget import QueryResultWidget
from ui.gui.workers import PriceWorker, QueryWorker, TransferWorker
from core.train_classifier import TrainClassifier
from utils.time_utils import is_cross_day as _is_cross_day


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
        self._is_querying = False  # 是否正在查询中（防止重复查询）
        self._is_transfer_querying = False  # 是否正在查询中转换乘
        self._transfer_loaded = False  # 中转查询是否已加载
        self._current_query_date = ""  # 当前查询日期（用于按需加载票价）

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("12306 车票查询与监控助手 v3.4.0")

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
        self.filter_panel = FilterPanel(station_dict, station_search_service=self.station_search)
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

        # 标签页：直达车次 / 中转换乘
        self.result_tabs = QTabWidget()

        # Tab 1: 直达车次
        self.result_widget = QueryResultWidget()
        self.result_widget.price_detail_requested.connect(self._on_price_detail_requested)
        self.result_widget.favorite_requested.connect(self._on_right_double_click_favorite)
        self.result_widget.unfavorite_requested.connect(self._on_unfavorite_request)
        self.result_tabs.addTab(self.result_widget, "直达车次")

        # Tab 2: 中转换乘
        self.transfer_widget = self._create_transfer_widget()
        self.result_tabs.addTab(self.transfer_widget, "中转换乘")

        # 标签切换时懒加载中转数据
        self.result_tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.result_tabs)
        return group

    def _create_transfer_widget(self) -> QWidget:
        """创建中转换乘显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 提示标签
        self.transfer_hint = QLabel("点击此标签页将自动查询中转换乘方案")
        self.transfer_hint.setStyleSheet("color: #888888; font-size: 12px; padding: 5px;")
        layout.addWidget(self.transfer_hint)

        # 中转结果表格
        self.transfer_table = QTableWidget()
        self.transfer_table.setColumnCount(10)
        self.transfer_table.setHorizontalHeaderLabels([
            "第一程车次", "第一程出发", "第一程到达", "第一程时间",
            "中转站", "等待时间",
            "第二程车次", "第二程出发", "第二程到达", "第二程时间"
        ])
        header = self.transfer_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(60)
        default_widths = {0: 80, 1: 70, 2: 70, 3: 120, 4: 70, 5: 80, 6: 80, 7: 70, 8: 70, 9: 120}
        for col, width in default_widths.items():
            self.transfer_table.setColumnWidth(col, width)
        self.transfer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.transfer_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transfer_table.setAlternatingRowColors(True)
        self.transfer_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        layout.addWidget(self.transfer_table)
        return widget

    def _on_tab_changed(self, index):
        """标签页切换回调"""
        # index 1 = 中转换乘标签
        if index == 1 and not self._transfer_loaded and self._has_queried:
            self._load_transfer_results()

    def _load_transfer_results(self):
        """异步加载中转换乘结果"""
        if self._is_transfer_querying:
            return

        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not from_station or not to_station:
            return

        self._is_transfer_querying = True
        self.transfer_hint.setText("正在查询中转方案，请稍候...")
        self.statusBar().showMessage("正在查询中转方案...")

        worker = TransferWorker(
            query_service=self.query_service,
            date=date,
            from_station=from_station,
            to_station=to_station
        )
        worker.signals.finished.connect(self._on_transfer_finished)
        worker.signals.error.connect(self._on_transfer_error)
        QThreadPool.globalInstance().start(worker)

    def _on_transfer_finished(self, result: dict):
        """中转换乘查询完成回调（主线程）"""
        try:
            if result.get("error"):
                if result["error"] == "STATION_NOT_FOUND":
                    self.transfer_hint.setText("中转查询失败：站名不存在，请检查输入")
                else:
                    self.transfer_hint.setText("中转查询失败，请稍后重试")
                self.statusBar().showMessage("中转查询失败")
                return

            transfers = result.get("transfers", [])
            self._update_transfer_display(transfers)
            self._transfer_loaded = True
            self.transfer_hint.setText(f"共找到 {len(transfers)} 个中转方案")
            self.statusBar().showMessage(f"中转查询完成 - 共 {len(transfers)} 个方案")
        finally:
            self._is_transfer_querying = False

    def _on_transfer_error(self, error_msg: str):
        """中转换乘查询异常回调（主线程）"""
        self._is_transfer_querying = False
        self.transfer_hint.setText(f"中转查询失败：{error_msg}")
        self.statusBar().showMessage("中转查询失败")
        if self.logger:
            self.logger.error(f"中转查询失败：{error_msg}")

    def _update_transfer_display(self, transfers: list):
        """更新中转表格显示"""
        self.transfer_table.setRowCount(0)
        for t in transfers:
            row = self.transfer_table.rowCount()
            self.transfer_table.insertRow(row)
            self.transfer_table.setItem(row, 0, QTableWidgetItem(t.first_leg.train_no))
            self.transfer_table.setItem(row, 1, QTableWidgetItem(t.first_leg.from_station))
            self.transfer_table.setItem(row, 2, QTableWidgetItem(t.first_leg.to_station))
            self.transfer_table.setItem(row, 3, QTableWidgetItem(
                f"{t.first_leg.departure_time} - {t.first_leg.arrival_time} ({t.first_leg.duration})"))
            self.transfer_table.setItem(row, 4, QTableWidgetItem(t.transfer_station))
            self.transfer_table.setItem(row, 5, QTableWidgetItem(t.wait_time or "--"))
            self.transfer_table.setItem(row, 6, QTableWidgetItem(t.second_leg.train_no))
            self.transfer_table.setItem(row, 7, QTableWidgetItem(t.second_leg.from_station))
            self.transfer_table.setItem(row, 8, QTableWidgetItem(t.second_leg.to_station))
            self.transfer_table.setItem(row, 9, QTableWidgetItem(
                f"{t.second_leg.departure_time} - {t.second_leg.arrival_time} ({t.second_leg.duration})"))

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
        self._transfer_loaded = False
        self.transfer_table.setRowCount(0)
        self.transfer_hint.setText("点击此标签页将自动查询中转换乘方案")

        # 重置筛选统计
        self.filter_result_label.setText("未筛选")

        # 重置状态
        self.status_label.setText("等待查询...")
        self.statusBar().showMessage("已重置查询条件")

    def _on_filter_changed(self):
        """筛选条件变化，实时过滤"""
        filter_config = self.filter_panel.get_filter_config()
        self.result_widget.apply_filters(filter_config)
        self._update_filter_label(filter_config)

    def _update_filter_label(self, filter_config: dict = None):
        """仅更新筛选统计标签（不重建表格）"""
        if filter_config is None:
            filter_config = self.filter_panel.get_filter_config()

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
        """执行查询（异步）"""
        # 防止重复查询（监控模式下定时器可能在上一次查询完成前再次触发）
        if getattr(self, '_is_querying', False):
            return

        from_station = self.from_station_input.text().strip()
        to_station = self.to_station_input.text().strip()
        date = self.date_picker.date().toString("yyyy-MM-dd")

        if not from_station or not to_station:
            QMessageBox.warning(self, "警告", "请输入出发站和到达站")
            return

        # 重置中转查询状态
        self._transfer_loaded = False
        self._current_query_date = date
        self._current_monitoring = monitoring

        # 立即更新 UI 为加载状态
        self._is_querying = True
        self.status_label.setText(f"正在查询：{from_station} -> {to_station} ({date}) ...")
        self.statusBar().showMessage("查询中...")
        self.query_button.setEnabled(False)

        # 提交后台查询任务
        worker = QueryWorker(
            query_service=self.query_service,
            date=date,
            from_station=from_station,
            to_station=to_station,
            bypass_cache=monitoring
        )
        worker.signals.finished.connect(self._on_query_finished)
        worker.signals.error.connect(self._on_query_error)
        QThreadPool.globalInstance().start(worker)

    def _on_query_finished(self, result: dict):
        """查询完成回调（主线程）"""
        try:
            monitoring = getattr(self, '_current_monitoring', False)

            if result.get("error"):
                if result["error"] == "STATION_NOT_FOUND":
                    QMessageBox.warning(self, "错误", "站名不存在，请检查输入")
                else:
                    QMessageBox.warning(self, "错误", "查询失败，请稍后重试")
                self._restore_query_button()
                return

            from_station = self.from_station_input.text().strip()
            to_station = self.to_station_input.text().strip()
            date = self._current_query_date

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

            # 同步更新筛选统计（不重建表格，set_data 已刷新）
            self._update_filter_label()

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
        finally:
            self._restore_query_button()

    def _on_query_error(self, error_msg: str):
        """查询异常回调（主线程）"""
        QMessageBox.critical(self, "错误", f"查询失败：{error_msg}")
        if self.logger:
            self.logger.error(f"GUI 查询失败：{error_msg}")
        self._restore_query_button()

    def _restore_query_button(self):
        """恢复查询按钮状态（非监控模式下启用）"""
        self._is_querying = False
        if not getattr(self, '_current_monitoring', False):
            self.query_button.setEnabled(True)

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

            # 跨天检测
            is_cross_day = _is_cross_day(ticket.departure_time, ticket.arrival_time, ticket.duration)

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
                'is_cross_day': is_cross_day,
                'has_ticket': bool(ticket.available_seats),
                'business_seat': ticket.available_seats.get('商/特', '--'),
                'first_seat': ticket.available_seats.get('一等座', '--'),
                'second_seat': ticket.available_seats.get('二等座', '--'),
                'soft_sleeper': ticket.available_seats.get('一等/软卧', '--'),
                'hard_sleeper': ticket.available_seats.get('二等/硬卧', '--'),
                'soft_seat': ticket.available_seats.get('软座', '--'),
                'hard_seat': ticket.available_seats.get('硬座', '--'),
                'no_seat': ticket.available_seats.get('无座', '--'),
                # 票价 API 所需字段
                'internal_train_no': getattr(ticket, 'internal_train_no', ''),
                'from_station_no': getattr(ticket, 'from_station_no', ''),
                'to_station_no': getattr(ticket, 'to_station_no', ''),
                'seat_types_code': getattr(ticket, 'seat_types_code', ''),
                # 票价信息
                'business_price': ticket.prices.get('商/特', '') if ticket.prices else '',
                'first_price': ticket.prices.get('一等座', '') if ticket.prices else '',
                'second_price': ticket.prices.get('二等座', '') if ticket.prices else '',
                'soft_sleeper_price': ticket.prices.get('一等/软卧', '') if ticket.prices else '',
                'hard_sleeper_price': ticket.prices.get('二等/硬卧', '') if ticket.prices else '',
                'hard_seat_price': ticket.prices.get('硬座', '') if ticket.prices else '',
                'no_seat_price': ticket.prices.get('无座', '') if ticket.prices else '',
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

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出结果", "", "JSON 文件 (*.json);;CSV 文件 (*.csv);;所有文件 (*)"
        )

        if file_path:
            try:
                from services.export_service import ExportService

                # 导出当前表格可见数据，保留用户筛选和排序后的结果。
                data = []
                for row in range(current_rows):
                    row_data = {}
                    for col in range(self.result_widget.table.columnCount()):
                        item = self.result_widget.table.item(row, col)
                        header_item = self.result_widget.table.horizontalHeaderItem(col)
                        if header_item:
                            header = header_item.text().replace(" ▲", "").replace(" ▼", "")
                            row_data[header] = item.text() if item else ""
                    data.append(row_data)

                lower_path = file_path.lower()
                if "csv" in selected_filter.lower() or lower_path.endswith(".csv"):
                    if not lower_path.endswith(".csv"):
                        file_path += ".csv"
                    ExportService.export_to_csv(data, file_path)
                else:
                    if not lower_path.endswith(".json"):
                        file_path += ".json"
                    ExportService.export_to_json(data, file_path)

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
            self._apply_notification_runtime_config()
            self.statusBar().showMessage("通知设置已保存")
            dialog.accept()

        save_button.clicked.connect(on_save)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def _apply_notification_runtime_config(self):
        """将通知设置立即应用到当前查询服务"""
        try:
            from notification import NotificationManager, NativeWindowsNotification
            from notification.channels import WeChatWorkNotification, FeishuNotification, DingTalkNotification

            notif_config = self.config_manager.get_config().get("notification", {})
            manager_config = {
                "enabled": notif_config.get("enabled", True),
                "cooldown_seconds": notif_config.get("cooldown_seconds", 300),
                "only_target_trains": notif_config.get("only_target_trains", False),
                "min_tickets": notif_config.get("min_tickets", 1),
                "target_trains": None,
            }
            notification_manager = NotificationManager(manager_config)
            channels_cfg = notif_config.get("channels", {})

            if channels_cfg.get("windows_desktop", {}).get("enabled", True):
                notification_manager.register_channel(NativeWindowsNotification())

            wx_cfg = channels_cfg.get("wechat_work", {})
            if wx_cfg.get("enabled") and wx_cfg.get("webhook_url"):
                notification_manager.register_channel(WeChatWorkNotification(wx_cfg["webhook_url"]))

            fs_cfg = channels_cfg.get("feishu", {})
            if fs_cfg.get("enabled") and fs_cfg.get("webhook_url"):
                notification_manager.register_channel(FeishuNotification(fs_cfg["webhook_url"]))

            dd_cfg = channels_cfg.get("dingtalk", {})
            if dd_cfg.get("enabled") and dd_cfg.get("webhook_url"):
                notification_manager.register_channel(
                    DingTalkNotification(dd_cfg["webhook_url"], dd_cfg.get("secret"))
                )

            self.query_service.notification_manager = notification_manager
            if self.logger:
                self.logger.info("通知设置已即时应用")
        except Exception as e:
            if self.logger:
                self.logger.error(f"通知设置即时应用失败：{e}", exc_info=True)
            QMessageBox.warning(self, "警告", f"通知设置已保存，但即时应用失败：{e}")

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

    def _on_price_detail_requested(self, ticket_data):
        """左键双击：异步加载并显示票价详情弹窗"""
        train_no = ticket_data.get('train_no', '')
        from_station = ticket_data.get('from_station', '')
        to_station = ticket_data.get('to_station', '')

        # 先显示弹窗（带加载提示）
        dialog = PriceDetailDialog(train_no, from_station, to_station, {}, self)

        # 异步获取票价
        worker = PriceWorker(
            self.query_service,
            ticket_data,
            self._current_query_date
        )
        worker.signals.finished.connect(lambda prices: dialog.update_prices(prices))
        QThreadPool.globalInstance().start(worker)

        dialog.exec()

    def _on_right_double_click_favorite(self, train_no):
        """右键双击：收藏/取消收藏"""
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
            "12306 车票查询与监控助手 v3.4.0\n\n"
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
