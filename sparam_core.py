import sys
import numpy as np
import skrf as rf
from scipy.signal import savgol_filter
from numpy.polynomial import Polynomial
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (QMessageBox, QDialog, QApplication,
                              QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox)


# === 网络变换 ===

def enforce_nonzero_impedance(network_ori, default_z0=50):
    """检查并处理阻抗矩阵中的零值，弹窗让用户选择替换值"""

    class ImpedanceDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("阻抗设置")
            layout = QVBoxLayout()
            self.label = QLabel("检测到阻抗矩阵中包含0值。\n请输入要使用的阻抗值(Ω):")
            layout.addWidget(self.label)
            self.input_box = QLineEdit(str(default_z0))
            self.input_box.setValidator(QDoubleValidator(0.1, 10000, 2))
            layout.addWidget(self.input_box)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok |
                QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
            self.setLayout(layout)

    z0_array = np.array(network_ori.z0)
    if not np.any(z0_array == 0):
        return

    app = QApplication.instance() or QApplication([])
    dialog = ImpedanceDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        try:
            new_z0 = float(dialog.input_box.text())
            if new_z0 <= 0:
                raise ValueError("阻抗值必须为正数")
            n_ports = network_ori.nports
            network_ori.z0 = np.ones((len(network_ori.f), n_ports)) * new_z0
            print(f"已将全部端口阻抗设置为 {new_z0}Ω")
        except ValueError as e:
            QMessageBox.warning(None, "输入错误", f"无效的阻抗值: {str(e)}")
    else:
        print("用户取消操作，保持原阻抗矩阵")


def enforce_nonzero_z0(network_ori, filepath):
    """检查并处理阻抗矩阵中的零值，从文件头行读取参考阻抗直接修正"""
    z0_array = np.array(network_ori.z0)
    if not np.any(z0_array == 0):
        return

    print("Zc_testing")
    new_z0 = None

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                tokens = line.split()
                try:
                    new_z0 = float(tokens[-1])
                except ValueError:
                    raise ValueError(f"无法解析参考阻抗: {line}")
                break

    if new_z0 is None:
        new_z0 = 50.0
        print("未在文件中找到 '#' 头行，使用默认参考阻抗 50Ω")

    n_ports = network_ori.nports
    network_ori.z0 = np.ones((len(network_ori.f), n_ports)) * new_z0
    print(f"检测到端口参考阻抗存在0，已将全部端口阻抗设置为 {new_z0}Ω")


def SE2diff(
        network_ori: rf.Network,
        port_mode='inside',
        output_mode='sdd_only',
        z0_diff=[100, 100]
) -> rf.Network:
    """将单端S参数转换为差分/混合模式"""
    enforce_nonzero_impedance(network_ori)
    network = network_ori.copy()
    n_ports = network.nports

    if port_mode == 'inline':
        port_shape = np.reshape(np.arange(n_ports), [2, n_ports // 2])
        port_order = port_shape.T.ravel()
        network.renumber(np.arange(n_ports), port_order)
    elif isinstance(port_mode, list):
        port_list = [x - 1 for x in port_mode]
        if len(port_list) != n_ports:
            raise ValueError(f"端口数量不匹配: 输入{len(port_mode)}个, 需要{n_ports}个")
        network.renumber(np.arange(n_ports), port_list)

    z01 = network.z0[0, 0]
    network.z0 = np.ones((len(network.f), n_ports)) * z01

    n_diff_port = n_ports // 2
    n_port_diff_side = n_diff_port // 2
    z0_diff_l = z0_diff[0]
    z0_diff_r = z0_diff[1]
    z0_comm_l = z0_diff_l / 4
    z0_comm_r = z0_diff_r / 4
    zdiff_vec_l = np.ones((1, n_port_diff_side)) * z0_diff_l
    zdiff_vec_r = np.ones((1, n_port_diff_side)) * z0_diff_r
    zcomm_vec_l = np.ones((1, n_port_diff_side)) * z0_comm_l
    zcomm_vec_r = np.ones((1, n_port_diff_side)) * z0_comm_r
    z_mix = np.hstack((zdiff_vec_l, zdiff_vec_r, zcomm_vec_l, zcomm_vec_r))
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))

    network.se2gmm(p=n_diff_port, z0_mm=z0_mix_matrix)

    port_names = network.port_names or [f"port_{i}" for i in range(1, n_ports + 1)]
    file_name = network.name

    if output_mode == 'sdd_only':
        new_network = network.subnetwork(ports=np.arange(n_diff_port))
        new_network.port_names = \
            [f'diff({a}, {b})' for a, b in zip(port_names[::2], port_names[1::2])]
        suffix = f'_sdd_Zdiff{z0_diff_l:.0f}_{z0_diff_r:.0f}ohm.s{n_diff_port}p'
    elif output_mode == 'full':
        new_network = network
        diff_names = [f'diff({a}, {b})' for a, b in zip(port_names[::2], port_names[1::2])]
        comm_names = [f'common({a}, {b})' for a, b in zip(port_names[::2], port_names[1::2])]
        new_network.port_names = diff_names + comm_names
        suffix = f'_mixed_Zdiff{z0_diff_l:.0f}_{z0_diff_r:.0f}ohm.s{n_ports}p'
    else:
        raise ValueError(f"无效的输出模式: {output_mode}")

    new_file_name = file_name.split('.')[0] + suffix
    new_network.name = new_file_name
    return new_network


def SE2dq_dqs(
        network_ori: rf.Network,
        line_list: list,
        port_mode='inside',
        z0_diff=[100, 100],
) -> rf.Network:
    """将多对单端线转换为差分模式（线逻辑）"""
    enforce_nonzero_impedance(network_ori)
    network = network_ori.copy()
    n_ports = network.nports
    n_lines = n_ports // 2
    n_diff = len(line_list)
    if not network.port_names:
        print('自动填充端口名称')
        network.port_names = [f"port_{i}" for i in range(1, n_ports + 1)]

    if not line_list:
        raise ValueError("至少需要指定一对差分线")

    if port_mode == 'inline':
        port_shape = np.reshape(np.arange(n_ports), [2, n_lines])
        port_order = port_shape.T.ravel()
        network.renumber(np.arange(n_ports), port_order)

    line_list = [i - 1 for i in line_list]
    diff_port_l = line_list
    diff_port_r = [i + n_lines for i in line_list]
    diff_ports = diff_port_l + diff_port_r
    print(f'转化为"inside"模式后的差分端口：{diff_ports}')

    all_ports = set(range(n_ports))
    non_diff_ports = sorted(list(all_ports - set(diff_ports)))
    new_port_order = diff_ports + non_diff_ports
    network.renumber(new_port_order, np.arange(n_ports))

    z0_diff_l, z0_diff_r = z0_diff
    zdiff_vec_l = np.ones((1, n_diff // 2)) * z0_diff_l
    zdiff_vec_r = np.ones((1, n_diff // 2)) * z0_diff_r
    zcomm_vec_l = np.ones((1, n_diff // 2)) * z0_diff_l / 4
    zcomm_vec_r = np.ones((1, n_diff // 2)) * z0_diff_r / 4
    z_mix = np.hstack((zdiff_vec_l, zdiff_vec_r, zcomm_vec_l, zcomm_vec_r))
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))

    network.se2gmm(p=n_diff, z0_mm=z0_mix_matrix)
    pn = network.port_names
    print(f'se2gmm后内置端口名称：')
    print(*pn, sep="\n")

    port_name_diff = [None] * n_diff
    port_name_comm = [None] * n_diff
    for i in range(n_diff):
        port_name_diff[i] = f'diff({pn[2 * i], pn[2 * i + 1]})'
        port_name_comm[i] = f'comm({pn[2 * i], pn[2 * i + 1]})'
    pn[0:n_diff] = port_name_diff
    pn[n_diff:2 * n_diff] = port_name_comm

    all_ports = set(range(n_ports))
    comm_set = set(range(n_diff, n_diff * 2))
    diff_se_ports = sorted(list(all_ports - comm_set))
    n_lines_new = len(diff_se_ports) // 2
    new_network = network.subnetwork(ports=diff_se_ports)

    ppo = list(range(n_ports - n_diff))
    for i in range(n_diff // 2):
        element = ppo.pop(n_diff // 2)
        print(element)
        ppo.insert(n_lines_new + n_diff // 2 - 1, element)
    new_network.renumber(ppo, list(range(n_ports - n_diff)))

    suffix = f'_partial_diff{z0_diff_l:.0f}_{z0_diff_r:.0f}ohm.s{len(diff_se_ports)}p'
    new_network.name = f"{network.name.split('.')[0]}{suffix}"
    return new_network


def SE2diff_port(
        network_ori: rf.Network,
        diff_list: list,
        z0_diff=100,
        output_mode='sdd_only'
) -> rf.Network:
    """将多对单端线转换为差分模式（端口逻辑）"""
    enforce_nonzero_impedance(network_ori)
    network = network_ori.copy()
    n_ports = network.nports

    if not diff_list:
        raise ValueError("至少需要指定一对差分端口")

    n_diff = len(diff_list) // 2
    diff_ports = [i - 1 for i in diff_list]
    print(f'差分端口序号(0-base)：{diff_ports}')

    all_ports = set(range(n_ports))
    non_diff_ports = sorted(list(all_ports - set(diff_ports)))
    new_port_order = diff_ports + non_diff_ports
    network.renumber(new_port_order, np.arange(n_ports))

    zdiff_vec = np.ones((1, n_diff)) * z0_diff
    zcomm_vec = np.ones((1, n_diff)) * z0_diff / 4
    z_mix = np.hstack((zdiff_vec, zcomm_vec))
    print(f'Zmm = {z_mix}')
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))

    network.se2gmm(p=n_diff, z0_mm=z0_mix_matrix)

    pn = network.port_names
    port_name_diff = [None] * n_diff
    port_name_comm = [None] * n_diff
    for i in range(n_diff):
        port_name_diff[i] = f'diff({pn[2 * i], pn[2 * i + 1]})'
        port_name_comm[i] = f'comm({pn[2 * i], pn[2 * i + 1]})'
    pn[0:n_diff] = port_name_diff
    pn[n_diff:2 * n_diff] = port_name_comm

    all_ports = set(range(n_ports))
    comm_set = set(range(n_diff, n_diff * 2))
    diff_se_ports = sorted(list(all_ports - comm_set))
    n_lines_new = len(diff_se_ports) // 2
    new_network = network.subnetwork(ports=diff_se_ports)

    ppo = list(range(n_ports - n_diff))
    for i in range(n_diff // 2):
        element = ppo.pop(n_diff // 2)
        print(element)
        ppo.insert(n_lines_new + n_diff // 2 - 1, element)
    new_network.renumber(ppo, list(range(n_ports - n_diff)))

    suffix = f'_partial_diff{z0_diff:.0f}ohm.s{len(diff_se_ports)}p'
    new_network.name = f"{network.name.split('.')[0]}{suffix}"
    return new_network


# === 纹波分析 ===

def ripple_calc(network, p1, p2, start_freqG, stop_freqG, data_mode, method, fit_params):
    """
    计算S参数纹波。
    fit_params 根据 method 不同包含:
        "n次多项式": {'order': 多项式阶数}
        "平滑函数":  {'window_length': 窗长度, 'polyorder': 阶数}
        "IEEE_std_802.3-2022": {}
    """
    s_params = network.s
    freqG = network.f / 1e9
    file_name = network.name
    s_param = s_params[:, p1 - 1, p2 - 1]
    label = f'{file_name.split("/")[-1]}_S{p1},{p2}'

    mask = (freqG >= start_freqG) & (freqG <= stop_freqG)
    freqG_range = freqG[mask]

    if data_mode == "幅度 (dB)":
        s_param_range = 20 * np.log10(np.abs(s_param[mask]))
    elif data_mode == "幅度 (abs)":
        s_param_range = np.abs(s_param[mask])
    elif data_mode == "unwrap相位 (度)":
        s_param_range = np.unwrap(np.angle(s_param[mask])) * 180 / np.pi
    elif data_mode == "unwrap相位 (rad)":
        s_param_range = np.unwrap(np.angle(s_param[mask]))
    else:
        raise ValueError("暂不支持该类型数据拟合")

    s_param_fit = s_param_range - s_param_range[0]

    result_fit = None
    if method == "n次多项式":
        coeffs = Polynomial.fit(freqG_range, s_param_fit, fit_params['order']).convert().coef
        fitted_curve = np.polyval(coeffs[::-1], freqG_range) + s_param_range[0]
    elif method == "IEEE_std_802.3-2022":
        result_fit = _ieee_8023_fit(freqG_range, s_param_fit)
        fitted_curve = result_fit['fitted_curve']
    elif method == "平滑函数":
        fitted_curve = savgol_filter(
            s_param_range,
            window_length=fit_params['window_length'],
            polyorder=fit_params['polyorder']
        )

    residuals = s_param_range - fitted_curve
    max_ripple = np.max(residuals)
    max_ripple_index = np.argmax(residuals)
    max_ripple_freqG = freqG_range[max_ripple_index]

    return {
        'label': label,
        'freqG_range': freqG_range,
        's_param_range': s_param_range,
        'fitted_curve': fitted_curve,
        'residuals': residuals,
        'max_ripple': max_ripple,
        'max_ripple_freqG': max_ripple_freqG,
        'max_ripple_index': max_ripple_index,
        'formula': result_fit['formula'] if result_fit else None
    }


def ripple_calc1(network, p1, p2, start_freqG, stop_freqG, data_mode, method, results, order):
    import matplotlib.pyplot as plt
    s_params = network.s
    freqG = network.f / 1e9
    file_name = network.name
    s_param = s_params[:, p1 - 1, p2 - 1]
    label = f'{file_name.split("/")[-1]}_S{p1},{p2}'

    mask = (freqG >= start_freqG) & (freqG <= stop_freqG)
    freqG_range = freqG[mask]

    if data_mode == "幅度 (dB)":
        s_param_range = 20 * np.log10(np.abs(s_param[mask]))
    elif data_mode == "幅度 (abs)":
        s_param_range = np.abs(s_param[mask])
    elif data_mode == "unwrap相位 (度)":
        s_param_range = np.unwrap(np.angle(s_param[mask])) * 180 / np.pi
    elif data_mode == "unwrap相位 (rad)":
        s_param_range = np.unwrap(np.angle(s_param[mask]))
    else:
        print("暂不支持该类型数据拟合")

    s_param_fit = s_param_range - s_param_range[0]

    result_fit = None
    if method == "n次多项式":
        coeffs = Polynomial.fit(freqG_range, s_param_fit, order).convert().coef
        fitted_curve = np.polyval(coeffs[::-1], freqG_range) + s_param_range[0]
    elif method == "IEEE_std_802.3-2022":
        result_fit = _ieee_8023_fit(freqG_range, s_param_fit)
        fitted_curve = result_fit['fitted_curve']

    residuals = np.abs(s_param_range - fitted_curve)
    max_ripple = np.max(residuals)
    max_ripple_index = np.argmax(residuals)
    max_ripple_freqG = freqG_range[max_ripple_index]

    results.append(f'{label}: ripple = {max_ripple:.4f} dB')

    plt.plot(freqG_range, s_param_range, label=label)
    plt.plot(freqG_range, fitted_curve, '--', label=f'{label} (拟合)')
    plt.plot(max_ripple_freqG, s_param_range[max_ripple_index], 'o')

    if method == "IEEE_std_802.3-2022" and result_fit:
        plt.annotate(
            result_fit['formula'],
            xy=(0.5, 0.95), xycoords='axes fraction',
            ha='center', va='top',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3)
        )
    return results


def _ieee_8023_fit(freqG, s_param_db):
    """IEEE 802.3-2022 标准拟合: IL(f) = a0 + a1*sqrt(f) + a2*f + a4*f^2"""
    freq = freqG * 1e9
    X = np.column_stack([
        np.ones_like(freq),
        np.sqrt(freq),
        freq,
        freq ** 2
    ])
    coeffs, _, _, _ = np.linalg.lstsq(X, s_param_db, rcond=None)
    fitted = (coeffs[0] +
              coeffs[1] * np.sqrt(freq) +
              coeffs[2] * freq +
              coeffs[3] * freq ** 2)
    return {
        'fitted_curve': fitted,
        'coeffs': {'a0': coeffs[0], 'a1': coeffs[1], 'a2': coeffs[2], 'a4': coeffs[3]},
        'formula': "IL(f) = {a0:.3f} + {a1:.3g}*√f + {a2:.3g}*f + {a4:.3g}*f^2".format(
            a0=coeffs[0], a1=coeffs[1], a2=coeffs[2], a4=coeffs[3])
    }


# === 端口字符串解析 ===

def parse_port_input1(input_str):
    """解析端口输入，支持 1:5、1:2:5、[1,2,5]、[1，2，5]、[1 2 5] 或 1 2 5"""
    try:
        cleaned = input_str.strip().strip('[]')
        if ':' in cleaned:
            parts = []
            for part in cleaned.split(':'):
                parts.extend(part.strip().split())
            parts = list(map(int, parts))
            if len(parts) == 2:
                return list(range(parts[0], parts[1] + 1))
            elif len(parts) == 3:
                return list(range(parts[0], parts[2] + 1, parts[1]))
            else:
                raise ValueError("冒号格式不正确")
        else:
            cleaned = cleaned.replace('，', ',')
            if ',' in cleaned:
                return [int(num.strip()) for num in cleaned.split(',') if num.strip()]
            else:
                numbers = cleaned.split()
                if numbers:
                    return list(map(int, numbers))
                else:
                    raise ValueError("输入为空")
    except ValueError as e:
        QMessageBox.warning(None, '输入错误',
                            f'端口输入格式错误！\n错误详情: {str(e)}\n'
                            '请输入以下格式之一:\n'
                            '1:5 (表示1到5，请确保为英文冒号)\n'
                            '1:2:5 (表示1到5，步长2)\n'
                            '[1,3,5] 或 [1 3 5] 或 1 3 5')
        return None


def parse_port_input(input_str, type='port'):
    """解析端口或频率输入，支持 1:5、1:2:5、[1,2,5]、空格分隔等多种格式"""
    try:
        cleaned = input_str.strip().strip('[]')
        cleaned = cleaned.replace('，', ',').replace('：', ':')
        convert = float if type == 'freq' else int

        if ':' in cleaned:
            parts = []
            for part in cleaned.split(':'):
                parts.extend(part.strip().split())
            parts = list(map(convert, parts))

            if len(parts) == 2:
                start, end = parts
                step = 1.0 if type == 'freq' else 1
            elif len(parts) == 3:
                start, step, end = parts
            else:
                raise ValueError("冒号格式不正确")

            if type == 'freq':
                result = []
                current = start
                while (step > 0 and current <= end) or (step < 0 and current >= end):
                    result.append(round(current, 10))
                    current += step
                return result
            else:
                return list(range(int(start), int(end) + 1, int(step)))
        else:
            if ',' in cleaned:
                return [convert(num.strip()) for num in cleaned.split(',') if num.strip()]
            else:
                numbers = cleaned.split()
                if numbers:
                    return list(map(convert, numbers))
                else:
                    raise ValueError("输入为空")

    except ValueError as e:
        QMessageBox.warning(None, '输入错误',
                            f'输入格式错误！\n错误详情: {str(e)}\n'
                            '请输入以下格式之一:\n'
                            '1:5 或 1:2:5（可用中文或英文冒号）\n'
                            '[1,3,5] 或 [1 3 5] 或 1 3 5')
        return None
