import sys
import os
import matplotlib

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("SKRF_PLOT_ENV", "none")


def main():
    matplotlib.rcParams['axes.unicode_minus'] = False
    if sys.platform == 'win32':
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        matplotlib.rcParams['mathtext.fontset'] = 'stix'
    else:
        matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']

    app = QApplication(sys.argv)
    from app_utils import resource_path
    from main_window import SParameterViewer_MainWin
    from runtime_services.trial_manager import check_trial_permission
    from runtime_services.version_manager import check_version_update_async

    app_icon = QIcon(resource_path("resources/ico_test.ico"))
    app.setWindowIcon(app_icon)
    if not check_trial_permission():
        sys.exit(1)

    viewer = SParameterViewer_MainWin(enable_time_domain=False)
    viewer.setWindowIcon(app_icon)
    viewer.show()
    viewer.info_version()
    QTimer.singleShot(300, lambda: check_version_update_async(parent=viewer))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
