import subprocess
import sys
from qtpy.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, QLabel,
                              QPlainTextEdit, QDialogButtonBox)


class PortNameDialog:
    """端口名称处理对话框，当检测到端口名称为空时，提供手动输入、自动生成或取消三种处理方式"""

    def __init__(self, parent, nports, file_name):
        self.parent = parent
        self.nports = nports
        self.file_name = file_name
        self.port_names = None

    def get_port_names(self):
        choice = self._ask_processing_method()
        if choice == "manual":
            if sys.platform == 'win32':
                subprocess.Popen(['notepad.exe', self.file_name])
            else:
                subprocess.Popen(['gvim', self.file_name])
            return self._show_edit_dialog(prefill_text=None)
        elif choice == "auto":
            auto_names = "\n".join([f"Port{i + 1}" for i in range(self.nports)])
            return self._show_edit_dialog(prefill_text=auto_names)
        else:
            return None

    def _ask_processing_method(self):
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle("端口名称缺失")
        msg_box.setText("未检测到端口名称，请选择处理方式：")
        manual_btn = msg_box.addButton("手动输入", QMessageBox.ButtonRole.ActionRole)
        auto_btn = msg_box.addButton("自动生成", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("不生成", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()
        clicked_btn = msg_box.clickedButton()
        if clicked_btn == manual_btn:
            return "manual"
        elif clicked_btn == auto_btn:
            return "auto"
        else:
            return "cancel"

    def _show_edit_dialog(self, prefill_text=None):
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("编辑端口名称")
        layout = QVBoxLayout()
        hint = "（已自动生成，可直接编辑）" if prefill_text else ""
        label = QLabel(f"请输入/检查 {self.nports} 个端口名称（每行一个）{hint}")
        text_edit = QPlainTextEdit()
        text_edit.setMinimumSize(400, 300)
        if prefill_text:
            text_edit.setPlainText(prefill_text)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(label)
        layout.addWidget(text_edit)
        layout.addWidget(button_box)
        dialog.setLayout(layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        port_names = [
            name.strip()
            for name in text_edit.toPlainText().split('\n')
            if name.strip()
        ]
        if len(port_names) != self.nports:
            QMessageBox.warning(
                self.parent, "数量不匹配",
                f"当前输入 {len(port_names)} 个名称，但需要 {self.nports} 个。"
            )
            return None
        return port_names
