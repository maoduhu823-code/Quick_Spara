import sys
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("SKRF_PLOT_ENV", "none")

# 旗标来源：命令行（--dev / --limited）或环境变量（QS_LIMITED=1）。
# 打包后 PyInstaller 用 runtime hook 注入 QS_LIMITED=1 → 自动进入精简版。
DEV_MODE = '--dev' in sys.argv
LIMITED_MODE = ('--limited' in sys.argv) or (os.environ.get('QS_LIMITED') == '1')


def _apply_dev_preset(viewer):
    """--dev 启动时预填一组本机调试用例。命令行没有该旗标的环境（包括冻结的 exe）绝不会触发。"""
    viewer.file_list.addItem('C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p')
    viewer.file_list.addItem('C:/Users/33202/PycharmProjects/Quick_Sparam/samples/Twinax line-Spara1G.s4p')
    viewer.port1_input.setText("1")
    viewer.port2_input.setText("2")


def main():
    app = QApplication(sys.argv)
    from app_utils import resource_path, configure_matplotlib
    configure_matplotlib()
    from main_window import SParameterViewer_MainWin
    from QS_runtime_services.trial_manager import check_trial_permission
    from QS_runtime_services.version_manager import check_version_update_async

    app_icon = QIcon(resource_path("resources/ico_test.ico"))
    app.setWindowIcon(app_icon)

    if not check_trial_permission():
        sys.exit(1)

    viewer = SParameterViewer_MainWin(enable_time_domain=not LIMITED_MODE)
    viewer.setWindowIcon(app_icon)
    if DEV_MODE:
        _apply_dev_preset(viewer)
    viewer.show()
    viewer.info_version()

    def run_startup_followups():
        if not LIMITED_MODE:
            viewer.prompt_usage_profile()
        check_version_update_async(parent=viewer)

    QTimer.singleShot(300, run_startup_followups)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
