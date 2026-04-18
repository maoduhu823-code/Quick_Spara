from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QProgressBar,
                             QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, QPropertyAnimation


class LoadingDialog(QDialog):
    def __init__(self, parent=None, title="请稍候", message="正在处理..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        self.setFixedSize(650, 150)
        self.cancelled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)

        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.message_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.animation = QPropertyAnimation(self.progress, b"value")
        self.animation.setDuration(2000)
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setLoopCount(-1)

    def showEvent(self, event):
        super().showEvent(event)
        self.animation.start()

    def closeEvent(self, event):
        self.animation.stop()
        super().closeEvent(event)

    def _on_cancel(self):
        self.cancelled = True
        self.close()

    def set_message(self, text):
        self.message_label.setText(text)
