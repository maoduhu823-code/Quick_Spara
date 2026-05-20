import sys
import os

from qtpy.QtCore import QTimer
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication

os.environ.setdefault("SKRF_PLOT_ENV", "none")

# 两种发行形态：
#   测试版：源码 + PyCharm 跑，加 --dev 预填一组本机调试用例。
#   安装版：PyInstaller 打包后的 exe，runtime hook 注入 QS_LIMITED=1 → 隐藏时域分析对话框入口。
DEV_MODE = '--dev' in sys.argv
LIMITED_MODE = os.environ.get('QS_LIMITED') == '1'

# --dev 强制进入本机路径模式，避免出差/借用机时被分发模式的共享盘配置劫持。
# 必须在 path_config 的消费者（main_window / usage_tracker 等）import 之前调用。
if DEV_MODE:
    from QS_runtime_services.path_config import force_local_mode
    force_local_mode(True)


def _apply_dev_preset(viewer):
    """--dev 启动时预填一组本机调试用例。命令行没有该旗标的环境（包括冻结的 exe）绝不会触发。"""
    viewer.file_list.addItem('C:/Users/33202/PycharmProjects/Quick_Sparam/samples/parallel_line.s16p')
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

    viewer = SParameterViewer_MainWin(
        enable_time_domain=True,
        enable_td_dialog=not LIMITED_MODE,
    )
    viewer.setWindowIcon(app_icon)
    if DEV_MODE:
        _apply_dev_preset(viewer)
    viewer.show()

    def run_startup_followups():
        viewer.prompt_usage_profile()
        check_version_update_async(parent=viewer)

    QTimer.singleShot(300, run_startup_followups)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
