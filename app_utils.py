import sys
import os
import traceback
import numpy as np
from PyQt6.QtWidgets import QMessageBox, QDialog, QApplication


# === 错误提示 ===

def show_error(parent, context_message=""):
    """显示带行号的错误弹窗"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    last_frame = traceback.extract_tb(exc_traceback)[-1]
    error_msg = (
        f"{context_message}\n\n"
        f"🛑 错误位置:\n"
        f"文件: {last_frame.filename}\n"
        f"行号: {last_frame.lineno}\n"
        f"函数: {last_frame.name}\n\n"
        f"💥 错误详情:\n{str(exc_value)}"
    )
    QMessageBox.critical(parent, '错误', error_msg)


# === 路径工具 ===

def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，适用于开发环境和 PyInstaller 打包环境。"""
    from QS_infra.resource_path import resource_path as _rp
    return _rp(relative_path)


# === matplotlib 配置 ===

def configure_matplotlib() -> None:
    """设置平台相关中文字体及负号渲染，幂等可重复调用。"""
    import matplotlib
    matplotlib.rcParams['axes.unicode_minus'] = False
    if sys.platform == 'win32':
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        matplotlib.rcParams.setdefault('mathtext.fontset', 'stix')
    else:
        matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']


def _get_pyplot():
    import matplotlib.pyplot as plt
    return plt


# === 绘图辅助 ===

def freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode="max"):
    """在频段内标注极值点，返回标注点和极值点信息"""
    mark_info = []
    worst_info = []
    for fG_mark in mark_freqGs:
        idx = np.abs(freqG - fG_mark).argmin()
        actual_freq = freqG[idx]
        actual_value = y_data[idx]
        mark_info.append({'freq': float(actual_freq), 'value': float(actual_value)})

        mask = (freqG <= fG_mark)
        band_freqG = freqG[mask]
        band_data = y_data[mask]

        if worst_mode == "max":
            worst_idx = np.argmax(band_data)
        else:
            worst_idx = np.argmin(band_data)
        worst_freqG = band_freqG[worst_idx]
        worst_value = band_data[worst_idx]

        ax.plot(worst_freqG, worst_value, 'ro', markersize=5)
        worst_info.append({'freq': float(worst_freqG), 'value': float(worst_value)})
    return mark_info, worst_info


def plot_main_curves(results_data, data_mode):
    """绘制主曲线（原始曲线和拟合曲线）"""
    plt = _get_pyplot()
    configure_matplotlib()
    plt.figure()
    for data in results_data:
        plt.plot(data['freqG_range'], data['s_param_range'], label=data['label'])
        plt.plot(data['freqG_range'], data['fitted_curve'], '--',
                 label=f"{data['label']} (拟合)")
        plt.plot(data['max_ripple_freqG'], data['s_param_range'][data['max_ripple_index']], 'o')
        if data['formula']:
            plt.annotate(
                data['formula'],
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3))
        plt.legend()
        plt.xlabel('频率 (GHz)')
        plt.ylabel(data_mode)
        plt.title('S参数曲线与拟合曲线')
        plt.grid(True)
        plt.show()


def plot_residuals(results_data, data_mode):
    """绘制残差曲线"""
    plt = _get_pyplot()
    configure_matplotlib()
    plt.figure()
    for data in results_data:
        plt.plot(data['freqG_range'], data['residuals'],
                 label=f"{data['label']} (ripple)")
    plt.legend()
    plt.xlabel('频率 (GHz)')
    plt.ylabel(data_mode)
    plt.title('S参数拟合Ripple')
    plt.grid(True)
    plt.show()


# === 端口UI工具 ===

def check_and_set_port_names(parent, file_list, network_service=None):
    """弹出端口选择器，返回排序后的端口索引列表(从1开始)，失败返回None。

    parent         : 任意 QWidget，作为对话框的父控件
    file_list      : 文件名/key 列表
    network_service: 可选 NetworkService；未传时降级回 parent.get_network()
    """
    from QS_dialogs.port_selector import PortSelector
    from QS_dialogs.port_name import PortNameDialog

    if not file_list:
        QMessageBox.warning(parent, "警告", "请先选择S参数文件")
        return None

    if len(file_list) > 1:
        QMessageBox.information(parent, "提示", "检测到多文件选择，将使用第一个文件的端口")

    try:
        if network_service is not None:
            network = network_service.get_network(file_list[0])
        else:
            network = parent.get_network(file_list[0])
    except Exception as e:
        QMessageBox.critical(parent, "错误", f"文件加载失败: {str(e)}")
        return None

    if not network.port_names:
        dialog = PortNameDialog(parent, network.nports, file_list[0])
        network.port_names = dialog.get_port_names()
        if not network.port_names:
            return None

    result, indices = PortSelector.select_ports(network.port_names, parent)
    if result != QDialog.DialogCode.Accepted or not indices:
        return None

    indices.sort()
    selected_names = [network.port_names[i - 1] for i in indices]
    print(f"\n=== 端口选择结果 ===")
    print(f"• 索引: {indices}\n• 名称: {', '.join(selected_names)}")
    QApplication.clipboard().setText(" ".join(map(str, indices)))
    return indices
