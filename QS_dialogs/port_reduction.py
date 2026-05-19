import sys
import numpy as np
from qtpy.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox, QMessageBox, QApplication)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QFont

from app_utils import show_error, check_and_set_port_names
from sparam_core import parse_port_input


class PortReductionDialog(QDialog):
    def __init__(self, parent=None, selected_sparams=None, network_service=None):
        super().__init__(parent)
        self.setWindowTitle("端口阻抗设置")
        self.resize(800, 500)
        self.setMinimumSize(QSize(600, 400))
        self.selected_sparams = selected_sparams or []
        self.result_data = None
        self._net_svc = network_service

        self.central_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self.create_table()

        self.button_layout = QHBoxLayout()
        self.add_button = QPushButton("➕ 添加端口组(行)")
        self.add_button.setFixedHeight(40)
        self.add_button.clicked.connect(self.add_port_row)
        self.delete_button = QPushButton("🗑️ 删除端口组(行)")
        self.delete_button.setFixedHeight(40)
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.set_port = QPushButton("选择端口名")
        self.set_port.setFixedHeight(40)
        self.set_port.clicked.connect(self.fill_by_name_selected)
        self.set_side_button = QPushButton("按侧排布")
        self.set_side_button.setFixedHeight(40)
        self.set_side_button.clicked.connect(self.arrange_by_side)
        self.set_line_button = QPushButton("按线排布")
        self.set_line_button.setFixedHeight(40)
        self.set_line_button.clicked.connect(self.arrange_by_line)
        self.generate_button = QPushButton("生成S参数")
        self.generate_button.setFixedHeight(40)
        self.generate_button.clicked.connect(self.generate_impedance_config)

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.set_port)
        self.button_layout.addWidget(self.set_side_button)
        self.button_layout.addWidget(self.set_line_button)
        self.button_layout.addWidget(self.generate_button)
        self.main_layout.addLayout(self.button_layout)

        for i in range(1):
            self.add_port_row(port_num=i + 1)

    def create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["端口序号", "端接阻抗 (Ω)", "端接电容 (pF)", "是否简并"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(0, 350)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        font = QFont()
        font.setPointSize(10)
        self.table.setFont(font)
        self.main_layout.addWidget(self.table)

    def delete_selected_rows(self):
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def add_port_row(self, port_num=None, enabled=False):
        row = self.table.rowCount()
        self.table.insertRow(row)

        port_item = QTableWidgetItem()
        if port_num is not None:
            port_item.setText(str(port_num))
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, port_item)

        impedance_item = QTableWidgetItem('50')
        impedance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, impedance_item)

        cap_item = QTableWidgetItem('0')
        cap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, cap_item)

        checkbox = QCheckBox()
        checkbox.setChecked(enabled)
        checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)
        self.table.setCellWidget(row, 3, widget)
        self.table.scrollToBottom()

    def _get_network(self, file_name):
        if self._net_svc is not None:
            return self._net_svc.get_network(file_name)
        return self.parent().get_network(file_name)

    def fill_by_name_selected(self):
        try:
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                QMessageBox.information(self, "提示", "请选择需要填入端口的行")
                return
            row = selected_indexes[-1].row()
            if row >= self.table.rowCount():
                return
            selected_ports = check_and_set_port_names(
                self, self.selected_sparams, network_service=self._net_svc)
            if selected_ports:
                self.table.item(row, 0).setText(" ".join(map(str, selected_ports)))
        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def arrange_by_side(self):
        try:
            network = self._get_network(self.selected_sparams[0])
            n_ports = network.nports
            if n_ports % 2 != 0:
                QMessageBox.warning(self, "警告", "端口数必须是偶数")
                return
            n = n_ports // 2
            self.table.setRowCount(0)
            self.add_port_row(port_num=f"1:{n}")
            self.add_port_row(port_num=f"{n + 1}:{n * 2}")
        except Exception as e:
            show_error(self, f"按侧排布时出错: {str(e)}")

    def arrange_by_line(self):
        try:
            network = self._get_network(self.selected_sparams[0])
            n_ports = network.nports
            if n_ports % 2 != 0:
                QMessageBox.warning(self, "警告", "端口数必须是偶数")
                return
            self.table.setRowCount(0)
            self.add_port_row(port_num=f"1:2:{n_ports - 1}")
            self.add_port_row(port_num=f"2:2:{n_ports}")
        except Exception as e:
            show_error(self, f"按线排布时出错: {str(e)}")

    def validate_inputs(self):
        """验证表格中所有输入是否有效"""
        all_ports = []
        for row in range(self.table.rowCount()):
            port_item = self.table.item(row, 0)
            if not port_item or not port_item.text():
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 端口号不能为空")
                self.table.selectRow(row)
                self.table.editItem(port_item)
                return False

            parsed_ports = parse_port_input(port_item.text())
            if parsed_ports is None:
                self.table.selectRow(row)
                self.table.editItem(port_item)
                return False

            for port in parsed_ports:
                if port <= 0:
                    QMessageBox.warning(self, "输入错误",
                                        f"第 {row + 1} 行: 端口号必须大于0 (检测到 {port})")
                    self.table.selectRow(row)
                    self.table.editItem(port_item)
                    return False
                if port in all_ports:
                    QMessageBox.warning(self, "输入错误",
                                        f"第 {row + 1} 行: 端口号 {port} 已重复")
                    self.table.selectRow(row)
                    self.table.editItem(port_item)
                    return False
                all_ports.append(port)

            impedance_item = self.table.item(row, 1)
            try:
                float(impedance_item.text())
            except ValueError:
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行: 电阻值必须是数字")
                self.table.selectRow(row)
                self.table.editItem(impedance_item)
                return False

            if self.table.columnCount() > 2:
                cap_item = self.table.item(row, 2)
                try:
                    c_val = float(cap_item.text())
                    if c_val < 0:
                        raise ValueError("电容值不能为负数")
                except ValueError as e:
                    QMessageBox.warning(self, "输入错误",
                                        f"第 {row + 1} 行: 电容值无效 ({e})")
                    self.table.selectRow(row)
                    self.table.editItem(cap_item)
                    return False
        return True

    def generate_impedance_config(self):
        if not self.validate_inputs():
            return
        try:
            self.port_configs = []
            self.z0_configs = []
            self.disabled_ports = []
            for row in range(self.table.rowCount()):
                ports = parse_port_input(self.table.item(row, 0).text())
                resistance = float(self.table.item(row, 1).text())
                capacitance = float(self.table.item(row, 2).text()) * 1e-12
                checkbox = self.table.cellWidget(row, 3).findChild(QCheckBox)
                Flag_subnetwork = checkbox.isChecked()
                self.port_configs.append(ports)
                self.z0_configs.append((resistance, capacitance))
                if Flag_subnetwork:
                    for port in ports:
                        self.disabled_ports.append(port)
            if not self.port_configs:
                QMessageBox.warning(self, "错误", "没有可用的端口设置")
                return
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成配置时出错:\n{str(e)}")

    def get_result(self):
        return self.port_configs, self.z0_configs, self.disabled_ports

    def compute_load_impedance(self, freq, z_rc):
        """计算 RC 并联负载阻抗向量"""
        R, C = z_rc
        omega = 2 * np.pi * freq
        if C == 0:
            return np.full_like(freq, R, dtype=complex)
        else:
            return R / (1 + 1j * omega * R * C)
