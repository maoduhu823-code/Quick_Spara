import subprocess
import sys

from PyQt6.QtWidgets import (
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QDialogButtonBox
)


class PortNameDialog:
    """
    端口名称处理对话框（提供三种处理方式）
    功能：当检测到端口名称为空时，允许用户选择手动输入、自动生成或取消操作
    """

    def __init__(self, parent, nports, file_name):
        """
        初始化对话框
        :param parent: 父窗口对象
        :param nports: 需要生成的端口数量
        """
        self.parent = parent  # 父窗口引用（用于模态对话框显示）
        self.nports = nports  # 端口总数
        self.file_name = file_name
        self.port_names = None  # 存储最终生成的端口名称列表

    def get_port_names(self):
        """主入口：获取端口名称（可能经过用户编辑）"""
        choice = self._ask_processing_method()

        if choice == "manual":
            if sys.platform == 'win32':
                subprocess.Popen(['notepad.exe', self.file_name])
            else:
                subprocess.Popen(['gvim', self.file_name])
            return self._show_edit_dialog(prefill_text=None)  # 完全手动模式
        elif choice == "auto":
            # 预填自动生成的名称（Port1, Port2...）
            auto_names = "\n".join([f"Port{i + 1}" for i in range(self.nports)])
            return self._show_edit_dialog(prefill_text=auto_names)  # 自动生成但可编辑
        else:
            return None

    def _ask_processing_method(self):
        """选择处理方式的初始对话框"""
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("端口名称缺失")
        msg_box.setText("未检测到端口名称，请选择处理方式：")

        manual_btn = msg_box.addButton("手动输入", QMessageBox.ButtonRole.ActionRole)
        auto_btn = msg_box.addButton("自动生成", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg_box.addButton("不生成", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked_btn = msg_box.clickedButton()

        if clicked_btn == manual_btn:
            return "manual"
        elif clicked_btn == auto_btn:
            return "auto"
        else:
            return "cancel"

    def _show_edit_dialog(self, prefill_text=None):
        """
        显示可编辑的文本输入对话框
        :param prefill_text: 预填的文本（自动生成时传入，手动时为None）
        :return: 处理后的端口名称列表（或None）
        """
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("编辑端口名称")
        layout = QVBoxLayout()

        # 提示信息（区分自动生成和手动模式）
        hint = "（已自动生成，可直接编辑）" if prefill_text else ""
        label = QLabel(f"请输入/检查 {self.nports} 个端口名称（每行一个）{hint}")

        # 文本输入框
        text_edit = QPlainTextEdit()
        text_edit.setMinimumSize(400, 300)
        if prefill_text:  # 如果是自动生成模式，预填内容
            text_edit.setPlainText(prefill_text)

        # 确定/取消按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        # 布局
        layout.addWidget(label)
        layout.addWidget(text_edit)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None  # 用户取消

        # 处理输入：按行分割，过滤空行和空格
        port_names = [
            name.strip()
            for name in text_edit.toPlainText().split('\n')
            if name.strip()
        ]

        # 验证数量
        if len(port_names) != self.nports:
            QMessageBox.warning(
                self.parent,
                "数量不匹配",
                f"当前输入 {len(port_names)} 个名称，但需要 {self.nports} 个。"
            )
            return None

        return port_names
