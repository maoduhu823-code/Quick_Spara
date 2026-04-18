from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget,
                             QAbstractItemView, QListWidgetItem)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag


class PortOrderEditor(QDialog):
    def __init__(self, port_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("端口顺序编辑器")
        self.port_names = port_names.copy()
        self.setup_ui()
        self.resize(400, 500)

    def setup_ui(self):
        layout = QVBoxLayout()

        # 说明标签
        label = QLabel("拖动列表项调整端口顺序（支持多选拖拽）：")
        layout.addWidget(label)

        # 可拖拽的列表控件（启用多选和拖拽）
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)  # 多选模式

        # 填充端口名称
        for name in self.port_names:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # 按钮区
        button_layout = QHBoxLayout()

        btn_ok = QPushButton("确定")
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_reset = QPushButton("重置顺序")
        btn_reset.clicked.connect(self.reset_order)

        button_layout.addWidget(btn_reset)
        button_layout.addStretch()
        button_layout.addWidget(btn_cancel)
        button_layout.addWidget(btn_ok)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def reset_order(self):
        """重置为原始顺序"""
        self.list_widget.clear()
        for name in self.port_names:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)

    def get_ordered_ports(self):
        """获取调整后的端口序号 (1-based)"""
        ordered_indices = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            original_index = self.port_names.index(item.data(Qt.ItemDataRole.UserRole))
            ordered_indices.append(original_index + 1)  # 1-based
        return ordered_indices


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    # 测试数据
    sample_ports = [f"Port_{i}" for i in range(1, 9)] + ["GND", "VCC"]

    app = QApplication(sys.argv)
    editor = PortOrderEditor(sample_ports)
    if editor.exec() == QDialog.DialogCode.Accepted:
        new_order = editor.get_ordered_ports()
        print("调整后的端口顺序 (1-based):", new_order)
        print("对应名称顺序:", [sample_ports[i - 1] for i in new_order])
    sys.exit(app.exec())
