import sys
import matplotlib

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from main_window import SParameterViewer_MainWin
from trial_manager import check_trial_permission
from version_manager import check_version_update


if __name__ == '__main__':
    matplotlib.rcParams['axes.unicode_minus'] = False
    if sys.platform == 'win32':
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        matplotlib.rcParams['mathtext.fontset'] = 'stix'
    else:
        matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']

    app = QApplication(sys.argv)
    if not check_trial_permission():
        sys.exit(1)

    viewer = SParameterViewer_MainWin()
    viewer.show()
    viewer.info_version()
    QTimer.singleShot(300, lambda: check_version_update(parent=viewer))

    sys.exit(app.exec())
