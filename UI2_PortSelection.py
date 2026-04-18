from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QListWidget,
                             QPushButton, QAbstractItemView, QMessageBox,
                             QHBoxLayout, QSizePolicy, QLabel)

from Basic_function_module import *


class PortSelector(QDialog):
    def __init__(self, port_names, parent=None):
        """
        参数:
            port_names: list - 端口名称列表
            parent: QWidget - 父窗口
        """
        super().__init__(parent)
        self.setWindowTitle("端口选择器")
        self.setModal(True)
        self.selected_indices = []  # 存储选中项的索引

        # 设置对话框尺寸
        self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.init_ui(port_names)


    def init_ui(self, port_names):
        """初始化UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 端口列表 (多选)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.list_widget.itemSelectionChanged.connect(self.update_selection)

        # 添加端口项
        for name in port_names:
            self.list_widget.addItem(name)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 全选按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_btn)

        # 取消选择按钮
        self.clear_selection_btn = QPushButton("清除选择")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(self.clear_selection_btn)

        # 确定按钮
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        button_layout.addWidget(self.confirm_btn)

        # 取消按钮
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        # 添加到主布局
        main_layout.addWidget(QLabel("请选择端口:"))
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def update_selection(self):
        """更新当前选择"""
        self.selected_indices = [i.row()+1 for i in self.list_widget.selectedIndexes()]

    def select_all(self):
        """全选所有端口"""
        self.list_widget.selectAll()
        self.update_selection()

    def clear_selection(self):
        """清除所有选择"""
        self.list_widget.clearSelection()
        self.selected_indices = []

    def get_selected_indices(self):
        """
        获取选中项的索引列表(从1开始)

        返回:
            list - 选中项的索引列表
        """
        return self.selected_indices

    @staticmethod
    def select_ports(port_names, parent=None):
        """
        静态方法方便调用

        参数:
            port_names: list - 端口名称列表
            parent: QWidget - 父窗口

        返回:
            tuple: (dialog_result, selected_indices)
                   dialog_result: QDialog.DialogCode
                   selected_indices: list - 选中索引列表(从0开始)
        """
        dialog = PortSelector(port_names, parent)
        result = dialog.exec()
        return (result, dialog.get_selected_indices())

    @classmethod
    def select_port(cls, port_names, self):
        pass
