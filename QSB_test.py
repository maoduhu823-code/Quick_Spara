# 仅用于开发调试，不作为打包入口

import sys
import os
import matplotlib

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("SKRF_PLOT_ENV", "none")

if __name__ == '__main__':
    matplotlib.rcParams['axes.unicode_minus'] = False
    if sys.platform == 'win32':
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        matplotlib.rcParams['mathtext.fontset'] = 'stix'
    else:
        matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']

    app = QApplication(sys.argv)
    from main_window import SParameterViewer_MainWin
    from QS_runtime_services.trial_manager import check_trial_permission
    from QS_runtime_services.version_manager import check_version_update_async

    if not check_trial_permission():
        sys.exit(1)

    viewer = SParameterViewer_MainWin()

    viewer.file_list.addItem('C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p')
    viewer.port1_input.setText("1")
    viewer.port2_input.setText("2")
    viewer.show()
    viewer.info_version()

    def run_startup_followups():
        viewer.prompt_usage_profile()
        check_version_update_async(parent=viewer)

    QTimer.singleShot(300, run_startup_followups)

    sys.exit(app.exec())
