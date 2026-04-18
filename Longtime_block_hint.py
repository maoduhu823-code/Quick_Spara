from PyQt6.QtWidgets import (QDialog, QLabel, QVBoxLayout, QProgressBar,
                             QHBoxLayout, QPushButton, QWidget)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation
from PyQt6.QtGui import QMovie


class LoadingDialog(QDialog):
    def __init__(self, parent=None, title="请稍候", message="正在处理..."):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        self.setFixedSize(650, 150)
        self.cancelled = False

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)

        # 消息标签
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.message_label)

        # 动态进度条（不确定模式）
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # 不确定进度模式
        layout.addWidget(self.progress)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # 添加动画效果
        self.animation = QPropertyAnimation(self.progress, b"value")
        self.animation.setDuration(2000)  # 2秒循环
        self.animation.setStartValue(0)
        self.animation.setEndValue(100)
        self.animation.setLoopCount(-1)  # 无限循环

    def showEvent(self, event):
        """显示对话框时启动动画"""
        super().showEvent(event)
        self.animation.start()

    def closeEvent(self, event):
        """关闭对话框时停止动画"""
        self.animation.stop()
        super().closeEvent(event)

    def _on_cancel(self):
        """取消按钮点击事件"""
        self.cancelled = True
        self.close()

    def set_message(self, text):
        """动态更新消息文本"""
        self.message_label.setText(text)


# ========== 使用示例 ==========
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout
    from PyQt6.QtCore import QThread, pyqtSignal
    import time
    import sys


    class WorkerThread(QThread):
        progress = pyqtSignal(str)
        finished = pyqtSignal()

        def run(self):
            for i in range(1, 6):
                if self.isInterruptionRequested():
                    break
                time.sleep(1)
                self.progress.emit(f"正在处理阶段 {i}/5...")
            self.finished.emit()


    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("主界面")
            self.resize(500, 300)

            central = QWidget()
            layout = QVBoxLayout()

            btn = QPushButton("开始任务")
            btn.clicked.connect(self.start_task)
            layout.addWidget(btn)

            central.setLayout(layout)
            self.setCentralWidget(central)

            # 初始化加载对话框（与主界面风格一致）
            self.loading_dialog = LoadingDialog(self)

        def start_task(self):
            # 重置并显示加载对话框
            self.loading_dialog.show()

            # 创建工作线程
            self.worker = WorkerThread()
            self.worker.progress.connect(self.loading_dialog.set_message)
            self.worker.finished.connect(self.on_task_finished)

            # 连接取消信号
            self.loading_dialog.cancel_btn.clicked.connect(
                lambda: self.worker.requestInterruption()
            )

            self.worker.start()

        def on_task_finished(self):
            self.loading_dialog.close()
            print("任务完成" if not self.loading_dialog.cancelled else "任务已取消")


    # 应用样式（与主界面一致）
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用系统标准样式

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
