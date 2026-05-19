# -*- coding: utf-8 -*-
from qtpy.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLabel, QDialogButtonBox, QMessageBox)
from qtpy.QtCore import Qt


class PortManagementDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("端口处理")
        self.setFixedWidth(440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        meta_group = QGroupBox("单点数据修改")
        meta_layout = QHBoxLayout()
        btn_names = QPushButton("编辑端口名")
        btn_names.clicked.connect(lambda: self.done(1))
        btn_z0 = QPushButton("修改参考阻抗")
        btn_z0.clicked.connect(lambda: self.done(2))
        meta_layout.addWidget(btn_names)
        meta_layout.addWidget(btn_z0)
        meta_group.setLayout(meta_layout)

        topo_group = QGroupBox("拓扑变换")
        topo_layout = QHBoxLayout()
        btn_reorder = QPushButton("端口重新排序")
        btn_reorder.clicked.connect(lambda: self.done(3))
        btn_merge = QPushButton("端口合并")
        btn_merge.clicked.connect(lambda: self.done(4))
        topo_layout.addWidget(btn_reorder)
        topo_layout.addWidget(btn_merge)
        topo_group.setLayout(topo_layout)

        imp_group = QGroupBox("阻抗变换&拓扑变换")
        imp_layout = QHBoxLayout()
        btn_reduction = QPushButton("重归一化/端口缩并")
        btn_reduction.setToolTip(
            "重新设置端口参考阻抗Zref（支持R//C结构）；"
            "删去不需要考虑的闲置端口")
        btn_reduction.clicked.connect(lambda: self.done(5))
        imp_layout.addWidget(btn_reduction)
        imp_group.setLayout(imp_layout)

        help_text = (
            "说明："
            "<修改参考阻抗>只改端口Z_ref的数值，不改变S参数矩阵；\n"
            "< 重归一化 > 会按新的参考阻抗重新计算S参数矩阵。\n"
            "< 端口合并 > 用于把多个物理端口并联成一个等效端口；\n"
            "< 端口缩并 > 用于将闲置端口按R/C条件端接后删除，降低端口数量。"
        )
        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "color: #4b5563; background: #f3f6fa; padding: 8px; "
            "border: 1px solid #d6dde8; border-radius: 4px;")

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.reject)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)

        layout.addWidget(meta_group)
        layout.addWidget(topo_group)
        layout.addWidget(imp_group)
        layout.addWidget(help_label)
        layout.addLayout(close_row)
        self.setLayout(layout)


class Z0EditDialog(QDialog):
    def __init__(self, parent, network):
        super().__init__(parent)
        self.setWindowTitle("修改参考阻抗")
        self.nports = network.nports
        self.current_z0 = abs(network.z0[0, :])
        self._result_z0 = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()

        warn_text = (
            "⚠ 此操作只修改参考阻抗标注，"
            "不重新归一化 S 矩阵。\n"
            "如需同时变换数据，请使用"
            "“重归一化/端口缩并”。"
        )
        warn = QLabel(warn_text)
        warn.setWordWrap(True)
        warn.setStyleSheet(
            "color: #b05000; background: #fff8e8; padding: 6px; border-radius: 4px;")
        layout.addWidget(warn)

        self.table = QTableWidget(self.nports, 3)
        self.table.setHorizontalHeaderLabels([
            "端口", "当前 Z0 (Ω)", "新 Z0 (Ω)"])
        for i, z0_val in enumerate(self.current_z0):
            self.table.setItem(i, 0, QTableWidgetItem(f"Port {i + 1}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{z0_val:.1f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{z0_val:.1f}"))
            for c in (0, 1):
                self.table.item(i, c).setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_accept(self):
        values = []
        for i in range(self.nports):
            try:
                val = float(self.table.item(i, 2).text())
                if val <= 0:
                    raise ValueError
                values.append(val)
            except (ValueError, AttributeError):
                QMessageBox.warning(
                    self, "输入错误",
                    f"Port {i + 1} 的阻抗值无效，请输入正数。")
                return
        self._result_z0 = values
        self.accept()

    def get_z0_values(self):
        return self._result_z0
