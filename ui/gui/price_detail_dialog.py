"""
票价详情弹窗
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton
)


class PriceDetailDialog(QDialog):
    """票价详情弹窗"""

    def __init__(self, train_no, from_station, to_station, prices, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"车次 {train_no} 票价详情")
        self.setFixedSize(350, 300)

        layout = QVBoxLayout(self)

        # 路线信息
        route_label = QLabel(f"{from_station} → {to_station}")
        route_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(route_label)

        # 票价表格
        price_table = QTableWidget()
        price_table.setColumnCount(2)
        price_table.setHorizontalHeaderLabels(["席别", "票价（元）"])
        header = price_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        price_table.setEditTriggers(QTableWidget.NoEditTriggers)
        price_table.setSelectionBehavior(QTableWidget.SelectRows)

        if prices:
            for seat_name, price_val in prices.items():
                if price_val:
                    row = price_table.rowCount()
                    price_table.insertRow(row)
                    price_table.setItem(row, 0, QTableWidgetItem(seat_name))
                    price_table.setItem(row, 1, QTableWidgetItem(f"¥{price_val}"))
        else:
            price_table.setRowCount(1)
            price_table.setSpan(0, 0, 1, 2)
            price_table.setItem(0, 0, QTableWidgetItem("暂无票价数据"))

        layout.addWidget(price_table)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def update_prices(self, prices):
        """异步加载完成后更新票价数据"""
        price_table = self.findChild(QTableWidget)
        if not price_table:
            return
        price_table.setRowCount(0)
        if prices:
            for seat_name, price_val in prices.items():
                if price_val:
                    row = price_table.rowCount()
                    price_table.insertRow(row)
                    price_table.setItem(row, 0, QTableWidgetItem(seat_name))
                    price_table.setItem(row, 1, QTableWidgetItem(f"¥{price_val}"))
        else:
            price_table.setRowCount(1)
            price_table.setSpan(0, 0, 1, 2)
            price_table.setItem(0, 0, QTableWidgetItem("暂无票价数据"))
