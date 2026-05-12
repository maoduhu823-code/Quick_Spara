from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QListWidget,
                             QPushButton, QAbstractItemView,
                             QHBoxLayout, QSizePolicy, QLabel)


class PortSelector(QDialog):
    def __init__(self, port_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("端口选择器")
        self.setModal(True)
        self.selected_indices = []
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.init_ui(port_names)

    def init_ui(self, port_names):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_selection)

        for name in port_names:
            self.list_widget.addItem(name)

        button_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("清除选择")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_selection_btn)

        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        button_layout.addWidget(self.confirm_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addWidget(QLabel("请选择端口:"))
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def update_selection(self):
        self.selected_indices = [i.row() + 1 for i in self.list_widget.selectedIndexes()]

    def select_all(self):
        self.list_widget.selectAll()
        self.update_selection()

    def clear_selection(self):
        self.list_widget.clearSelection()
        self.selected_indices = []

    def get_selected_indices(self):
        """返回选中项的索引列表（从1开始）"""
        return self.selected_indices

    @staticmethod
    def select_ports(port_names, parent=None):
        """静态便捷方法，返回 (dialog_result, selected_indices)"""
        dialog = PortSelector(port_names, parent)
        result = dialog.exec()
        return (result, dialog.get_selected_indices())
