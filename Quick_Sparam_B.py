from PyQt6.QtWidgets import QApplication
from Basic_function_module import *
from Quick_Sparam_mainUI import SParameterViewer_MainWin
import matplotlib as plt

import os


if __name__ == '__main__':
    # plt.rcParams['mathtext.fontset'] = 'stix'  # 设置数学字体为STIX
    # plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
    # plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    if sys.platform == 'win32':
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 仅影响普通文本
        plt.rcParams['mathtext.fontset'] = 'stix'  # 仅影响数学符号
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # 仅影响普通文本

    app = QApplication(sys.argv)
    viewer = SParameterViewer_MainWin()
    viewer.show()
    viewer.info_version()
    if not viewer.check_beta_period():
        sys.exit(1)

    # ============调试时设置的默认输入，生成app时记得删除============
    # viewer.file_list.addItem('E:\工作\SD8026V100\model\Sparameter\SD8026V110_0607_HostTx.s16p')
    # viewer.file_list.addItem('E:\工作\历史项目\HiMaxwell_SSD_SD\分段建模\Sparameters\PCB_1812E\Ball_DramSide.s24p')
    # viewer.file_list.addItem('E:\个人文件\Python\Quick_Sparam\DavidV120_Master_IVR_0415_PVDD_DVDD18_09_041825_004620_14846_DCfitted.s95p')
    # viewer.file_list.setCurrentRow(0)
    # viewer.port1_input.setText("1")
    # viewer.port2_input.setText("1")
    # ============调试时设置的默认输入，生成app时记得删除============

    sys.exit(app.exec())