import sys
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("SKRF_PLOT_ENV", "none")


if __name__ == '__main__':
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

    viewer = SParameterViewer_MainWin()
    viewer.setWindowIcon(app_icon)
    viewer.show()
    viewer.info_version()

    def run_startup_followups():
        viewer.prompt_usage_profile()
        check_version_update_async(parent=viewer)

    QTimer.singleShot(300, run_startup_followups)

    sys.exit(app.exec())
