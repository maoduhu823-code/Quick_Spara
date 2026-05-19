from qtpy.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget,
                             QAbstractItemView, QListWidgetItem)
from qtpy.QtCore import Qt


class PortOrderEditor(QDialog):
    def __init__(self, port_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("端口顺序编辑器")
        self.port_names = port_names.copy()
        self.setup_ui()
        self.resize(400, 500)

    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("拖动列表项调整端口顺序（支持多选拖拽）：")
        layout.addWidget(label)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        for name in self.port_names:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        btn_reset = QPushButton("重置顺序")
        btn_reset.clicked.connect(self.reset_order)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("确定")
        btn_ok.clicked.connect(self.accept)

        button_layout.addWidget(btn_reset)
        button_layout.addStretch()
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def reset_order(self):
        self.list_widget.clear()
        for name in self.port_names:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

    def get_ordered_ports(self):
        """返回调整后的端口序号（1-based）"""
        ordered_indices = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            original_index = self.port_names.index(item.data(Qt.ItemDataRole.UserRole))
            ordered_indices.append(original_index + 1)
        return ordered_indices
