"""
筛选面板组件
模仿 12306 网站样式，提供车次类型、车站、席别、时段等筛选功能
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QGroupBox,
    QScrollArea, QFrame, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class FilterPanel(QWidget):
    """筛选面板组件"""

    # 筛选条件变化信号
    filter_changed = Signal()

    def __init__(self, station_dict: dict = None):
        super().__init__()
        self.station_dict = station_dict or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 车次类型筛选
        self._create_train_type_group(layout)

        # 出发站筛选
        self._create_from_station_group(layout)

        # 到达站筛选
        self._create_to_station_group(layout)

        # 席别筛选
        self._create_seat_type_group(layout)

        # 发车时段筛选
        self._create_time_period_group(layout)

    def _create_train_type_group(self, parent_layout):
        """创建车次类型筛选组"""
        group = QGroupBox("车次类型")
        layout = QGridLayout(group)

        # 车次类型复选框（带字头显示）
        self.train_type_checks = {}
        train_types = [
            ("GC", "高铁/城际 - G/C"),
            ("D", "动车 - D"),
            ("Z", "直达 - Z"),
            ("T", "特快 - T"),
            ("K", "快速 - K"),
            ("其他", "其他"),
        ]

        for i, (key, text) in enumerate(train_types):
            cb = QCheckBox(text)
            cb.setChecked(True)  # 默认全选
            cb.stateChanged.connect(self._on_filter_changed)
            self.train_type_checks[key] = cb
            layout.addWidget(cb, i // 3, i % 3)

        # 复兴号和智能动车组单独一行
        self.is_fuxing_check = QCheckBox("复兴号")
        self.is_fuxing_check.setChecked(True)
        self.is_fuxing_check.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.is_fuxing_check, 2, 0)

        self.is_smart_check = QCheckBox("智能动车组")
        self.is_smart_check.setChecked(True)
        self.is_smart_check.stateChanged.connect(self._on_filter_changed)
        layout.addWidget(self.is_smart_check, 2, 1)

        parent_layout.addWidget(group)

    def _create_from_station_group(self, parent_layout):
        """创建出发站筛选组"""
        group = QGroupBox("出发站")
        layout = QVBoxLayout(group)

        # 搜索框
        self.from_station_search = QLineEdit()
        self.from_station_search.setPlaceholderText("搜索出发站...")
        self.from_station_search.textChanged.connect(self._update_from_stations)
        layout.addWidget(self.from_station_search)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 复选框容器
        self.from_station_container = QWidget()
        self.from_station_layout = QGridLayout(self.from_station_container)
        self.from_station_layout.setAlignment(Qt.AlignTop)

        self.from_station_checks = {}
        self._init_station_checks(self.from_station_checks, self.from_station_layout)

        scroll.setWidget(self.from_station_container)
        layout.addWidget(scroll)
        parent_layout.addWidget(group)

    def _create_to_station_group(self, parent_layout):
        """创建到达站筛选组"""
        group = QGroupBox("到达站")
        layout = QVBoxLayout(group)

        # 搜索框
        self.to_station_search = QLineEdit()
        self.to_station_search.setPlaceholderText("搜索到达站...")
        self.to_station_search.textChanged.connect(self._update_to_stations)
        layout.addWidget(self.to_station_search)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(120)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 复选框容器
        self.to_station_container = QWidget()
        self.to_station_layout = QGridLayout(self.to_station_container)
        self.to_station_layout.setAlignment(Qt.AlignTop)

        self.to_station_checks = {}
        self._init_station_checks(self.to_station_checks, self.to_station_layout)

        scroll.setWidget(self.to_station_container)
        layout.addWidget(scroll)
        parent_layout.addWidget(group)

    def _init_station_checks(self, checks_dict, layout):
        """初始化车站复选框（初始时不显示任何车站）"""
        # 不再显示全国车站，初始为空
        checks_dict.clear()
        # 清空布局
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def update_stations(self, from_stations: list = None, to_stations: list = None):
        """
        更新车站列表
        :param from_stations: 出发站列表
        :param to_stations: 到达站列表
        """
        # 更新出发站
        if from_stations is not None:
            self._update_station_checks(self.from_station_checks, self.from_station_layout,
                                        search_text="", station_list=from_stations)

        # 更新到达站
        if to_stations is not None:
            self._update_station_checks(self.to_station_checks, self.to_station_layout,
                                        search_text="", station_list=to_stations)

    def _update_from_stations(self, search_text):
        """更新出发站复选框显示"""
        self._update_station_checks(self.from_station_checks, self.from_station_layout, search_text)

    def _update_to_stations(self, search_text):
        """更新到达站复选框显示"""
        self._update_station_checks(self.to_station_checks, self.to_station_layout, search_text)

    def _update_station_checks(self, checks_dict, layout, search_text, station_list=None):
        """更新车站复选框"""
        # 清除现有复选框
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        checks_dict.clear()

        # 确定车站列表
        if station_list is not None:
            stations = sorted(station_list)
        elif search_text:
            stations = sorted(self.station_dict.keys())
            if search_text:
                kw = search_text.lower()
                stations = [s for s in stations if kw in s.lower() or
                           any(kw in pinyin for pinyin in self._get_pinyin_initials(s))]
        else:
            # 没有查询结果且无搜索文本，不显示任何车站
            return

        # 重新创建复选框（限制数量）
        for i, station in enumerate(stations[:100]):
            cb = QCheckBox(station)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_changed)
            checks_dict[station] = cb
            layout.addWidget(cb, i // 5, i % 5)

    def _get_pinyin_initials(self, station: str) -> list:
        """获取车站拼音首字母和全拼"""
        try:
            from pypinyin import lazy_pinyin, Style
            initials = ''.join(lazy_pinyin(station, style=Style.FIRST_LETTER)).lower()
            full = ''.join(lazy_pinyin(station)).lower()
            return [initials, full]
        except Exception:
            return []

    def _create_seat_type_group(self, parent_layout):
        """创建席别筛选组"""
        group = QGroupBox("席别")
        layout = QGridLayout(group)

        self.seat_checks = {}
        seat_types = [
            ("business", "商务座"),
            ("first", "一等座"),
            ("second", "二等座"),
            ("soft_sleeper", "软卧"),
            ("hard_sleeper", "硬卧"),
            ("no_seat", "无座"),
        ]

        for i, (key, text) in enumerate(seat_types):
            cb = QCheckBox(text)
            cb.setChecked(True)  # 默认全选
            cb.stateChanged.connect(self._on_filter_changed)
            self.seat_checks[key] = cb
            layout.addWidget(cb, i // 3, i % 3)

        parent_layout.addWidget(group)

    def _create_time_period_group(self, parent_layout):
        """创建发车时段筛选组"""
        group = QGroupBox("发车时间")
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel("时段:"))

        self.time_period_combo = QComboBox()
        self.time_period_combo.addItems([
            "00:00-24:00",
            "00:00-06:00",
            "06:00-12:00",
            "12:00-18:00",
            "18:00-24:00"
        ])
        self.time_period_combo.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self.time_period_combo)
        layout.addStretch()

        parent_layout.addWidget(group)

    def _on_filter_changed(self):
        """筛选条件变化"""
        self.filter_changed.emit()

    def get_filter_config(self) -> dict:
        """获取当前筛选配置"""
        # 车次类型
        train_types = [k for k, v in self.train_type_checks.items() if v.isChecked()]

        # 出发站
        from_stations = [k for k, v in self.from_station_checks.items() if v.isChecked()]
        all_from_stations = list(self.from_station_checks.keys())

        # 到达站
        to_stations = [k for k, v in self.to_station_checks.items() if v.isChecked()]
        all_to_stations = list(self.to_station_checks.keys())

        # 席别
        seat_types = [k for k, v in self.seat_checks.items() if v.isChecked()]

        # 发车时段
        time_period = self.time_period_combo.currentText()

        # 复兴号/智能动车组筛选
        # 注意：这两个是显示标识，不是筛选条件
        show_fuxing = self.is_fuxing_check.isChecked()
        show_smart = self.is_smart_check.isChecked()

        return {
            'train_types': train_types,
            'from_stations': from_stations,
            'all_from_stations': all_from_stations,
            'to_stations': to_stations,
            'all_to_stations': all_to_stations,
            'seat_types': seat_types,
            'time_period': time_period,
            'show_fuxing': show_fuxing,
            'show_smart': show_smart,
        }

    def reset_filters(self):
        """重置所有筛选条件"""
        # 车次类型全选
        for cb in self.train_type_checks.values():
            cb.setChecked(True)

        # 复兴号/智能动车组全选
        self.is_fuxing_check.setChecked(True)
        self.is_smart_check.setChecked(True)

        # 出发站全选
        for cb in self.from_station_checks.values():
            cb.setChecked(True)

        # 到达站全选
        for cb in self.to_station_checks.values():
            cb.setChecked(True)

        # 席别全选
        for cb in self.seat_checks.values():
            cb.setChecked(True)

        # 时段重置为全部
        self.time_period_combo.setCurrentIndex(0)

        # 清空搜索框
        self.from_station_search.clear()
        self.to_station_search.clear()

        # 重新初始化车站列表
        self._init_station_checks(self.from_station_checks, self.from_station_layout)
        self._init_station_checks(self.to_station_checks, self.to_station_layout)

        self.filter_changed.emit()
