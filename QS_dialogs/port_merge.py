import numpy as np
from qtpy.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QApplication)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QFont

from app_utils import show_error, check_and_set_port_names
from sparam_core import parse_port_input


class PortMergeDialog(QDialog):
    """
    端口并联合并对话框。
    每行定义一个合并组：
        列0 — 端口序号（1-based，支持 1 2 3 / 1:3 / 1:2:5 格式）
        列1 — 合并后新端口参考阻抗 (Ω)，默认 50
    支持多行，即多组同时合并。
    """

    def __init__(self, parent=None, selected_sparams=None, network_service=None):
        super().__init__(parent)
        self.setWindowTitle("端口合并")
        self.resize(700, 400)
        self.setMinimumSize(QSize(500, 300))
        self.selected_sparams = selected_sparams or []
        self._net_svc = network_service
        self._port_groups  = []   # list[list[int]]  1-based，accept 后有效
        self._z0_list      = []   # list[float]

        self.central_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        self._create_table()
        self._create_buttons()
        self.add_port_row()

    # ── 控件构建 ────────────────────────────────────────────────────────────

    def _create_table(self):
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["合并端口序号（1-based）", "参考阻抗 (Ω)"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 130)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked
                                   | QTableWidget.EditTrigger.SelectedClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        font = QFont()
        font.setPointSize(10)
        self.table.setFont(font)
        self.main_layout.addWidget(self.table)

    def _create_buttons(self):
        layout = QHBoxLayout()

        add_btn = QPushButton("➕ 添加合并组(行)")
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self.add_port_row)

        del_btn = QPushButton("🗑️ 删除选中行")
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self.delete_selected_rows)

        pick_btn = QPushButton("选择端口名")
        pick_btn.setFixedHeight(38)
        pick_btn.clicked.connect(self.fill_by_name_selected)

        gen_btn = QPushButton("生成S参数")
        gen_btn.setFixedHeight(38)
        gen_btn.clicked.connect(self._generate)

        for btn in (add_btn, del_btn, pick_btn, gen_btn):
            layout.addWidget(btn)
        self.main_layout.addLayout(layout)

    # ── 行操作 ──────────────────────────────────────────────────────────────

    def add_port_row(self, port_text=""):
        row = self.table.rowCount()
        self.table.insertRow(row)

        port_item = QTableWidgetItem(str(port_text) if port_text else "")
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, port_item)

        z0_item = QTableWidgetItem("50")
        z0_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, z0_item)

        self.table.scrollToBottom()

    def delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return
        for r in rows:
            self.table.removeRow(r)

    def fill_by_name_selected(self):
        try:
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                QMessageBox.information(self, "提示", "请先选中需要填入端口号的行")
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

    # ── 验证与生成 ───────────────────────────────────────────────────────────

    def _validate(self):
        all_ports = []
        for row in range(self.table.rowCount()):
            port_item = self.table.item(row, 0)
            if not port_item or not port_item.text().strip():
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行：端口序号不能为空")
                self.table.selectRow(row)
                return False

            ports = parse_port_input(port_item.text())
            if ports is None:
                self.table.selectRow(row)
                return False
            if len(ports) < 2:
                QMessageBox.warning(self, "输入错误",
                                    f"第 {row + 1} 行：每个合并组至少需要 2 个端口")
                self.table.selectRow(row)
                return False
            for p in ports:
                if p <= 0:
                    QMessageBox.warning(self, "输入错误",
                                        f"第 {row + 1} 行：端口号必须大于 0（检测到 {p}）")
                    return False
                if p in all_ports:
                    QMessageBox.warning(self, "输入错误",
                                        f"第 {row + 1} 行：端口号 {p} 在多个合并组中重复")
                    return False
            all_ports.extend(ports)

            z0_item = self.table.item(row, 1)
            try:
                val = float(z0_item.text())
                if val <= 0:
                    raise ValueError("参考阻抗必须大于0")
            except ValueError as e:
                QMessageBox.warning(self, "输入错误", f"第 {row + 1} 行：{e}")
                self.table.selectRow(row)
                return False
        return True

    def _generate(self):
        if not self._validate():
            return
        self._port_groups = []
        self._z0_list     = []
        for row in range(self.table.rowCount()):
            self._port_groups.append(parse_port_input(self.table.item(row, 0).text()))
            self._z0_list.append(float(self.table.item(row, 1).text()))
        self.accept()

    def get_result(self):
        """返回 (port_groups_1based: list[list[int]], z0_list: list[float])"""
        return self._port_groups, self._z0_list
