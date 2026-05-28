"""
查询结果表格组件
支持排序、筛选、收藏高亮、右键菜单等功能
"""

from typing import List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMenu
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor

from utils.time_utils import time_to_minutes, duration_to_minutes


class QueryResultWidget(QWidget):
    """查询结果表格组件"""

    price_detail_requested = Signal(dict)  # 左键双击：请求显示票价详情
    favorite_requested = Signal(str)        # 右键双击：请求收藏/取消收藏
    unfavorite_requested = Signal(str)      # 取消收藏请求（右键菜单触发）

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

        # 设置列宽 - Interactive 模式支持横向滚动
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(50)

        # 为每列设置合理的默认宽度
        default_widths = {
            0: 80,    # 车次
            1: 70,    # 出发站
            2: 70,    # 到达站
            3: 55,    # 开点
            4: 60,    # 到点（跨天时显示"次日 HH:MM"，需要更宽）
            5: 55,    # 历时
            6: 90,    # 商务座/特等座
            7: 70,    # 一等座
            8: 70,    # 二等座
            9: 100,   # 软卧/动卧/一等卧
            10: 90,   # 硬卧/二等卧
            11: 55,   # 软座
            12: 70,   # 硬座
            13: 65,   # 无座
        }
        for col, width in default_widths.items():
            self.table.setColumnWidth(col, width)

        # 启用横向滚动条
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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

        # 安装事件过滤器以捕获右键双击
        self.table.viewport().installEventFilter(self)

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

    def _sort_data(self, column):
        """执行排序"""
        if not self.current_data:
            return

        # 定义排序键函数
        def get_sort_key(item):
            # 收藏车次优先的标记
            is_favorite = item['train_no'].upper() in getattr(self, 'favorites_set', set())
            fav_priority = 0 if is_favorite else 1

            if column == 3:  # 开点
                time_val = time_to_minutes(item.get('departure_time', '99:99'))
                return (fav_priority, time_val)
            elif column == 4:  # 到点（需处理跨天）
                arrival_val = time_to_minutes(item.get('arrival_time', '99:99'))
                depart_val = time_to_minutes(item.get('departure_time', '99:99'))
                duration_val = duration_to_minutes(item.get('duration', '99:99'))
                if arrival_val < depart_val and duration_val > 0:
                    arrival_val += 24 * 60
                return (fav_priority, arrival_val)
            elif column == 5:  # 历时
                duration_val = duration_to_minutes(item.get('duration', '99:99'))
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
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        try:
            # 始终使用 filtered_data 显示
            data_to_show = self.filtered_data if self.filtered_data else self.current_data
            favorites_set = getattr(self, 'favorites_set', set())

            # 预分配行数，避免逐行 insertRow 的开销
            self.table.setRowCount(len(data_to_show))

            for row_idx, ticket in enumerate(data_to_show):
                train_no = ticket['train_no']
                has_ticket = ticket.get('has_ticket', False)
                is_favorite = train_no.upper() in favorites_set

                # 预计算行背景色
                if is_favorite:
                    row_color = QColor(255, 255, 200)  # 黄色
                elif has_ticket:
                    row_color = QColor(200, 255, 200)  # 绿色
                else:
                    row_color = QColor(240, 240, 240)  # 灰色

                # 构建车次显示（含"复"、"智"标识，用小字）
                train_display = train_no
                if ticket.get('is_fuxing', False):
                    train_display += " 复"
                if ticket.get('is_smart', False):
                    train_display += " 智"

                # 设置数据，直接在创建时应用背景色
                items = [
                    (0, train_display),
                    (1, ticket.get('from_station', '--')),
                    (2, ticket.get('to_station', '--')),
                    (3, ticket.get('departure_time', '--')),
                    (4, f"次日 {ticket.get('arrival_time', '--')}" if ticket.get('is_cross_day', False) and ticket.get('arrival_time', '--') != '--' else ticket.get('arrival_time', '--')),
                    (5, ticket.get('duration', '--')),
                    (6, ticket.get('business_seat', '--')),
                    (7, ticket.get('first_seat', '--')),
                    (8, ticket.get('second_seat', '--')),
                    (9, ticket.get('soft_sleeper', '--')),
                    (10, ticket.get('hard_sleeper', '--')),
                    (11, ticket.get('soft_seat', '--')),
                    (12, ticket.get('hard_seat', '--')),
                    (13, ticket.get('no_seat', '--')),
                ]
                for col, text in items:
                    item = QTableWidgetItem(text)
                    item.setBackground(row_color)
                    self.table.setItem(row_idx, col, item)
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.blockSignals(False)
            self.table.setSortingEnabled(True)

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

        # 检查是否已收藏
        is_favorite = train_no_clean.upper() in getattr(self, 'favorites_set', set())

        menu = self.table.createStandardContextMenu()

        if is_favorite:
            # 添加分隔符
            menu.addSeparator()
            # 添加取消收藏动作
            unfavorite_action = menu.addAction("取消收藏")
            unfavorite_action.triggered.connect(lambda: self.unfavorite_requested.emit(train_no_clean))

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _on_double_click(self, index):
        """处理左键双击事件 — 显示票价详情"""
        row = index.row()
        data_to_use = self.filtered_data if self.filtered_data else self.current_data
        if 0 <= row < len(data_to_use):
            self.price_detail_requested.emit(data_to_use[row])

    def eventFilter(self, obj, event):
        """事件过滤器 — 捕获右键双击实现收藏"""
        if obj == self.table.viewport() and event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.RightButton:
            row = self.table.rowAt(event.position().toPoint().y())
            if row >= 0:
                train_no_item = self.table.item(row, 0)
                if train_no_item:
                    train_no_raw = train_no_item.text().strip()
                    train_no = train_no_raw.split()[0]
                    self.favorite_requested.emit(train_no)
                    return True
        return super().eventFilter(obj, event)

    def set_data(self, tickets: List[Dict], favorites: List[str] = None):
        """
        设置表格数据
        :param tickets: 车票数据列表（解析后的结构化数据）
        :param favorites: 收藏车次列表
        """
        if favorites is None:
            favorites = []

        self.favorites = favorites  # 保存收藏列表用于右键菜单
        self.favorites_set = set(f.upper() for f in favorites)  # 预计算集合用于 O(1) 查找

        # 保存原始数据用于排序和筛选
        # 排序：收藏车次优先（预计算 upper_train_no 避免重复调用）
        self.current_data = sorted(tickets, key=lambda x: (x['train_no'].upper() not in self.favorites_set, x['departure_time']))
        self.filtered_data = self.current_data

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
