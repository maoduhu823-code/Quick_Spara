import sys
from qtpy.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QComboBox, QGroupBox)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QFont, QColor

from app_utils import show_error
from sparam_core import parse_port_input


class CascadeDialog(QDialog):
    def __init__(self, parent=None, selected_sparams=None, network_service=None):
        super().__init__(parent)
        self.setWindowTitle("S参数级联设置")
        self.resize(1200, 500)
        self.setMinimumSize(QSize(600, 400))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setModal(True)
        self.cascade_configs = []
        self.selected_sparams = selected_sparams or []
        self._net_svc = network_service

        self.central_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self.create_operation_buttons()
        self.create_table()
        self.create_action_buttons()
        self.auto_generate_rows()

    def create_operation_buttons(self):
        group = QGroupBox("端口信息：表格相同颜色的格子表示端口相连")
        layout = QHBoxLayout()

        self.all_ports_btn = QPushButton("所有端口")
        self.all_ports_btn.setToolTip("填充为1:nports")
        self.all_ports_btn.clicked.connect(self.fill_all_ports)
        self.side_arrange_btn = QPushButton("按边排布")
        self.side_arrange_btn.clicked.connect(self.fill_side_arranged_ports)
        self.line_arrange_btn = QPushButton("按线排布")
        self.line_arrange_btn.clicked.connect(self.fill_line_arranged_ports)
        self.swap_ports_btn = QPushButton("左右交换")
        self.swap_ports_btn.clicked.connect(self.swap_ports)
        self.on_port_name = QPushButton("选择端口名")
        self.on_port_name.clicked.connect(self.fill_by_name_selected)

        layout.addWidget(self.all_ports_btn)
        layout.addWidget(self.side_arrange_btn)
        layout.addWidget(self.line_arrange_btn)
        layout.addWidget(self.swap_ports_btn)
        layout.addWidget(self.on_port_name)
        group.setLayout(layout)
        self.main_layout.addWidget(group)

    def create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["S参数文件", "级联端口序号1", "级联端口序号2"])
        self.table.setColumnWidth(0, 800)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 170)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        font = QFont()
        font.setPointSize(10)
        self.table.setFont(font)
        self.main_layout.addWidget(self.table)

    def set_pair_colors(self):
        row_count = self.table.rowCount()
        if row_count < 2:
            return
        COLOR_PALETTE = [
            QColor(0, 123, 255), QColor(40, 167, 69), QColor(255, 193, 7),
            QColor(220, 53, 69), QColor(23, 162, 184), QColor(108, 117, 125),
            QColor(255, 87, 34), QColor(156, 39, 176),
        ]

        def color_generator():
            idx = 0
            while True:
                yield COLOR_PALETTE[idx % len(COLOR_PALETTE)]
                idx += 1

        color_iter = color_generator()
        for i in range(row_count - 1):
            color = next(color_iter)
            item_right = self.table.item(i, 2)
            if item_right is None:
                item_right = QTableWidgetItem()
                self.table.setItem(i, 2, item_right)
            item_right.setBackground(color)

            item_left = self.table.item(i + 1, 1)
            if item_left is None:
                item_left = QTableWidgetItem()
                self.table.setItem(i + 1, 1, item_left)
            item_left.setBackground(color)

    def create_action_buttons(self):
        self.button_layout = QHBoxLayout()
        self.add_button = QPushButton("➕ 添加级联")
        self.add_button.setFixedHeight(40)
        self.add_button.clicked.connect(self.add_cascade_row)
        self.delete_button = QPushButton("🗑️ 删除选中")
        self.delete_button.setFixedHeight(40)
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.confirm_button = QPushButton("✅ 确认配置")
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.clicked.connect(self.confirm_cascade_config)
        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.confirm_button)
        self.main_layout.addLayout(self.button_layout)

    def auto_generate_rows(self):
        for i, sparam in enumerate(self.selected_sparams):
            self.add_cascade_row(default_sparam=sparam, default_port=str(i + 1))
        self.set_pair_colors()

    def delete_selected_rows(self):
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def add_cascade_row(self, default_sparam=None, default_port=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        combo = QComboBox()
        combo.addItems(self.selected_sparams)
        if default_sparam:
            index = combo.findText(default_sparam)
            if index >= 0:
                combo.setCurrentIndex(index)
        self.table.setCellWidget(row, 0, combo)
        port1_item = QTableWidgetItem(default_port if default_port else "")
        port1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, port1_item)
        port2_item = QTableWidgetItem("")
        port2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, port2_item)
        self.table.scrollToBottom()
        self.set_pair_colors()

    def fill_all_ports(self):
        try:
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                return
            for index in selected_indexes:
                row = index.row()
                column = index.column()
                if row >= self.table.rowCount():
                    continue
                combo = self.table.cellWidget(row, 0)
                if not combo:
                    continue
                sparam_file = combo.currentText()
                nports = int(sparam_file.split('.')[-1][1:-1])
                if self.table.item(row, column):
                    self.table.item(row, column).setText(f"1:{nports}")
                else:
                    self.table.setItem(row, column, QTableWidgetItem(f"1:{nports}"))
        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def fill_side_arranged_ports(self):
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()})
        for row in selected_rows:
            if row >= self.table.rowCount():
                continue
            combo = self.table.cellWidget(row, 0)
            sparam_file = combo.currentText()
            try:
                nports = int(sparam_file.split('.')[-1][1:-1])
                half = nports // 2
                self.table.item(row, 1).setText(f"1:{half}")
                self.table.item(row, 2).setText(f"{half + 1}:{nports}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def fill_line_arranged_ports(self):
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()})
        for row in selected_rows:
            if row >= self.table.rowCount():
                continue
            combo = self.table.cellWidget(row, 0)
            sparam_file = combo.currentText()
            try:
                nports = int(sparam_file.split('.')[-1][1:-1])
                self.table.item(row, 1).setText(f"1:2:{nports - 1}")
                self.table.item(row, 2).setText(f"2:2:{nports}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def swap_ports(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        try:
            for row in rows:
                port1 = self.table.item(row, 1).text()
                port2 = self.table.item(row, 2).text()
                self.table.item(row, 1).setText(port2)
                self.table.item(row, 2).setText(port1)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def fill_by_name_selected(self):
        try:
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                return
            for index in selected_indexes:
                row = index.row()
                column = index.column()
                if row >= self.table.rowCount():
                    continue
                combo = self.table.cellWidget(row, 0)
                if not combo:
                    continue
                sparam_file = combo.currentText()
                from app_utils import check_and_set_port_names
                selected_ports = check_and_set_port_names(
                    self, [sparam_file], network_service=self._net_svc)
                if selected_ports:
                    text_str = " ".join(map(str, selected_ports))
                    self.table.item(row, column).setText(text_str)
        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def confirm_cascade_config(self):
        try:
            self.cascade_configs = []
            for row in range(self.table.rowCount()):
                combo = self.table.cellWidget(row, 0)
                sparam_file = combo.currentText()
                ports_left = parse_port_input(self.table.item(row, 1).text())
                ports_right = parse_port_input(self.table.item(row, 2).text())
                if not ports_left or not ports_right:
                    QMessageBox.warning(self, "错误", f"第 {row + 1} 行端口设置不完整")
                    return
                self.cascade_configs.append({
                    'sparam_file': sparam_file,
                    'ports_left': ports_left,
                    'ports_right': ports_right
                })
            for i in range(len(self.cascade_configs) - 1):
                right_len = len(self.cascade_configs[i]['ports_right'])
                next_left_len = len(self.cascade_configs[i + 1]['ports_left'])
                if right_len != next_left_len:
                    QMessageBox.critical(
                        self, "端口不匹配",
                        f"第 {i + 1} 行右端口数为 {right_len}，\n"
                        f"但第 {i + 2} 行左端口数为 {next_left_len}，不匹配！"
                    )
                    return
            if not self.cascade_configs:
                QMessageBox.warning(self, "错误", "没有可用的级联设置")
                return
            print("级联配置数据:")
            for config in self.cascade_configs:
                print(f"S参数文件: {config['sparam_file']}")
                print(f"级联端口——左{config['ports_left']}，右{config['ports_right']}")
            self.accept()
        except Exception:
            show_error(self, "生成配置时出错")

    def get_result(self):
        return self.cascade_configs
