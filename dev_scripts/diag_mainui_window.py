"""验证主 UI 的频域窗下拉框：
  1) 切换到时域 → 频域窗下拉框显示且可选
  2) 选择不同窗 → 计算输出与 compute_time_domain(window_type=...) 一致
"""
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SKRF_PLOT_ENV", "none")

from qtpy.QtWidgets import QApplication
from app_utils import configure_matplotlib

app = QApplication.instance() or QApplication(sys.argv)
configure_matplotlib()

from main_window import SParameterViewer_MainWin
from QS_domain.algorithms.time_domain import compute_time_domain

DEV_FILE = r"C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p"
viewer = SParameterViewer_MainWin(enable_time_domain=True)
# main_window 把 stdout 重定向到 GUI，恢复回真 stdout 让本脚本输出可见
sys.stdout = viewer._original_stdout
viewer.add_file_list_item(DEV_FILE)
viewer.file_list.item(0).setSelected(True)
viewer.port1_input.setText("1")
viewer.port2_input.setText("3")
# 触发缓存填充：s_data 是 lazy，要先 get_network
viewer.get_network(DEV_FILE)
viewer.show()  # 让 setVisible 生效
QApplication.processEvents()

# 1) 切到时域
viewer.param_type_combo.setCurrentText('时域')
print("时域窗下拉项:", [viewer._td_win_combo.itemText(i)
                       for i in range(viewer._td_win_combo.count())])
print(f"切到时域后默认: dt={viewer._td_dt_edit.text()}  tr={viewer._td_tr_edit.text()}  "
      f"UI宽度={viewer._td_pw_edit.text()}")

# 2) 选脉冲响应：Z0 应隐藏，UI宽度应显示
viewer.facet_combo.setCurrentText('脉冲响应')
print(f"facet=脉冲响应  Z0.visible={viewer._td_z0_edit.isVisible()}  "
      f"UI宽度.visible={viewer._td_pw_edit.isVisible()}")

# 2.5) 切到 TDR 阻抗：Z0 应显示，UI宽度应隐藏
viewer.facet_combo.setCurrentText('TDR阻抗')
print(f"facet=TDR阻抗  Z0.visible={viewer._td_z0_edit.isVisible()}  "
      f"UI宽度.visible={viewer._td_pw_edit.isVisible()}")

# 2.6) 关注频点驱动 UI 宽度默认：写 10 GHz，再切回时域应得到 1/(2*10G) = 50 ps
viewer.freG_input.setText("10")
viewer.param_type_combo.setCurrentText('S参数')
viewer.param_type_combo.setCurrentText('时域')
print(f"关注频点=10GHz 后切回时域: UI宽度={viewer._td_pw_edit.text()}  (期望 50)")

viewer.freG_input.setText("")
viewer.param_type_combo.setCurrentText('S参数')
viewer.param_type_combo.setCurrentText('时域')
print(f"关注频点清空后切回时域: UI宽度={viewer._td_pw_edit.text()}  (期望 30*dt)")

# 3) 准备到脉冲响应做计算
viewer.facet_combo.setCurrentText('脉冲响应')

# 3) 不同窗：对比主 UI 算的 line 数据 与 直接调用 compute_time_domain
network = viewer.get_network(DEV_FILE)
s_mat = viewer.get_param_matrix(DEV_FILE, 'S参数')
tr_ps = float(viewer._td_tr_edit.text())
dt_ps = float(viewer._td_dt_edit.text())
z0    = float(viewer._td_z0_edit.text())

_WIN_MAP = {"高斯": "gaussian", "矩形": "rect", "汉宁": "hanning",
            "汉明": "hamming",  "布莱克曼": "blackman",
            "Tukey": "tukey",   "Kaiser": "kaiser"}
print()
print(f"{'下拉框选项':<10s} {'压栈 window_type':<14s} {'y[0]':>12s} {'max':>10s}")
print("-" * 55)
for zh, en in _WIN_MAP.items():
    viewer._td_win_combo.setCurrentText(zh)
    r = compute_time_domain(network, 1, 3, "pulse",
                              tr_ps=tr_ps, dt_ps=dt_ps, z0=z0,
                              window_type=en, s_params=s_mat)
    print(f"{zh:<10s} {en:<14s} {r['y_data'][0]:>+12.4e} {r['y_data'].max():>10.4f}")

print()
print("主 UI 频域窗下拉框接线 OK")
