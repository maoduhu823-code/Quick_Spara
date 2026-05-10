"""
自动化UI测试脚本：验证新功能
测试文件: input_test/diff_line.s4p
运行方式: python test_new_features.py
"""
import sys
import os
import skrf

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

sys.path.insert(0, os.path.dirname(__file__))
from main_window import SParameterViewer_MainWin

TEST_FILE = os.path.join(os.path.dirname(__file__),
                         'input_test', 'diff_line.s4p')
DELAY = 1000  # ms between steps

app = QApplication(sys.argv)
viewer = SParameterViewer_MainWin()
viewer.show()

t = 0

def s(fn):
    global t
    t += DELAY
    QTimer.singleShot(t, fn)


def step_load():
    net = skrf.Network(TEST_FILE)
    fname = os.path.basename(TEST_FILE)
    viewer.s_data[fname] = net
    viewer.file_list.addItem(fname)
    viewer.file_list.setCurrentRow(0)
    print(f'[TEST 1] 文件已加载: {fname}  ({net.nports}端口)')


def step_plot_s_db():
    viewer.port1_input.setText('1')
    viewer.port2_input.setText('2')
    viewer.param_type_combo.setCurrentText('S参数')
    # 等 facet_combo 更新后选 幅度(dB)
    viewer.facet_combo.setCurrentIndex(0)
    viewer.plot_button.click()
    print('[TEST 2] S参数 幅度(dB) 绘图完成，验证: 曲线出现在新窗口')


def step_plot_z_imp():
    viewer.param_type_combo.setCurrentText('Z参数')
    viewer.facet_combo.setCurrentText('阻抗(mΩ)')
    print(f'[TEST 3] Z参数 阻抗(mΩ)  X轴={viewer.xscale_combo.currentText()} '
          f'Y轴={viewer.yscale_combo.currentText()}（应均为"对数"）')
    viewer.plot_button.click()
    print('[TEST 3] 验证: 坐标轴为 log-log')


def step_freq_list():
    print('[TEST 4] 点击频点列表')
    viewer.btn_freq_list.click()
    print('[TEST 4] 验证: console 打印出频率表格')


def step_freq_slice():
    print('[TEST 5] 频域切片 → 将弹出输入框，请输入: 1~5')
    viewer.call_freq_slice()
    print('[TEST 5] 验证: 出现 2×2 subplot 图')


def step_port_mgmt():
    print('[TEST 6] 打开端口处理对话框，验证: 3个 QGroupBox 分区')
    viewer.call_port_management()
    print('[TEST 6] （模态对话框关闭后继续）')


def step_file_info():
    print('[TEST 7] 点击文件信息按钮')
    viewer.Basic_info.click()
    print('[TEST 7] 验证: console 打印文件名/频率范围/端口名/Z_ref')


s(step_load)
s(step_plot_s_db)
s(step_plot_z_imp)
s(step_freq_list)
s(step_freq_slice)       # 弹出 QInputDialog，需手动输入频率范围
t += 4000                # 留时间关闭频域切片图
s(step_port_mgmt)        # 模态对话框，需手动选择操作或关闭
t += 5000                # 留时间关闭端口处理对话框
s(step_file_info)

sys.exit(app.exec())
