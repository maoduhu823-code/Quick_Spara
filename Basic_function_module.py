# Basic_function_module.py
import sys
import numpy as np
import traceback
import os
import sys
import numpy as np
import skrf as rf
from typing import Tuple, Dict, Union
import matplotlib.pyplot as plt
from PyQt6.QtGui import QDoubleValidator
from scipy.signal import savgol_filter
from numpy.polynomial import Polynomial
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QDialog, QApplication
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel,
                             QLineEdit, QDialogButtonBox)

# region Description


def enforce_nonzero_impedance(network_ori, default_z0=50):
    """
    检查并处理阻抗矩阵中的零值

    参数:
        network_ori: 原始网络对象
        default_z0: 默认建议的阻抗值(Ω)

    返回:
        None (直接修改原网络对象)
    """

    class ImpedanceDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("阻抗设置")
            layout = QVBoxLayout()

            self.label = QLabel(
                "检测到阻抗矩阵中包含0值。\n"
                "请输入要使用的阻抗值(Ω):"
            )
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

    # 检查是否存在0阻抗
    z0_array = np.array(network_ori.z0)
    if not np.any(z0_array == 0):
        return  # 没有零值则直接返回

    # 创建并显示对话框
    app = QApplication.instance() or QApplication([])
    dialog = ImpedanceDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        try:
            new_z0 = float(dialog.input_box.text())
            if new_z0 <= 0:
                raise ValueError("阻抗值必须为正数")

            # 设置统一阻抗
            n_ports = network_ori.nports
            network_ori.z0 = np.ones((len(network_ori.f), n_ports)) * new_z0
            print(f"已将全部端口阻抗设置为 {new_z0}Ω")

        except ValueError as e:
            QMessageBox.warning(None, "输入错误", f"无效的阻抗值: {str(e)}")
            return
    else:
        print("用户取消操作，保持原阻抗矩阵")


def enforce_nonzero_z0(network_ori, filepath):
    """
    检查并处理阻抗矩阵中的零值,直接修改

    参数:
        network_ori: 原始网络对象
        filepath: Touchstone 文件路径

    返回:
        None (直接修改原网络对象)
    """
    # 检查是否存在0阻抗
    z0_array = np.array(network_ori.z0)
    if not np.any(z0_array == 0):
        return  # 没有零值则直接返回

    print("Zc_testing")

    new_z0 = None  # 显式初始化，防止未定义

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                tokens = line.split()
                try:
                    new_z0 = float(tokens[-1])
                except ValueError:
                    raise ValueError(
                        f"无法解析参考阻抗: {line}"
                    )
                break  # ← 关键：读到 # 行立即退出循环

    # 如果文件中没有 '#' 行，使用安全默认值
    if new_z0 is None:
        new_z0 = 50.0
        print("未在文件中找到 '#' 头行，使用默认参考阻抗 50Ω")

    # 设置统一阻抗
    n_ports = network_ori.nports
    network_ori.z0 = np.ones((len(network_ori.f), n_ports)) * new_z0

    print(f"检测到端口参考阻抗存在0，已将全部端口阻抗设置为 {new_z0}Ω")


# 单端转差分
def SE2diff(
        network_ori: rf.Network,
        port_mode='inside',
        output_mode='sdd_only',
        z0_diff=[100, 100]
) -> rf.Network:
    """
    将单端S参数转换为差分/混合模式

    参数:
        network: 原始单端网络
        port_mode: 端口模式 ('inline' 或自定义端口列表)
        output_mode: 输出模式 ('sdd_only' 或 'full')
        z0_diff: 差模阻抗

    返回:
        转换后的网络
    """
    enforce_nonzero_impedance(network_ori)
    network = network_ori.copy()
    n_ports = network.nports

    # 端口重排序
    if port_mode == 'inline':
        # inline模式: 1,2为线1; 3,4为线2...
        port_shape = np.reshape(np.arange(n_ports), [2, n_ports // 2])
        port_order = port_shape.T.ravel()
        network.renumber(np.arange(n_ports), port_order)
    elif isinstance(port_mode, list):
        # 自定义端口顺序
        port_list = [x - 1 for x in port_mode]  # 转换为0-based
        if len(port_list) != n_ports:
            # 后续改为提示端口不相等，是否进行部分端口的差分
            raise ValueError(
                f"端口数量不匹配: 输入{len(port_mode)}个, 需要{n_ports}个"
            )
        network.renumber(np.arange(n_ports), port_list)

    # 强制阻抗矩阵为满阵
    z01 = network.z0[0, 0]
    # print(f'强制阻抗矩阵非零: Z_ref={z01}')
    network.z0 = np.ones((len(network.f), n_ports)) * z01

    # 计算混合模式阻抗矩阵
    n_diff_port = n_ports // 2
    n_port_diff_side = n_diff_port // 2
    # 后续改为支持端口阻抗向量输入
    z0_diff_l = z0_diff[0]
    z0_diff_r = z0_diff[1]
    z0_comm_l = z0_diff_l/4
    z0_comm_r = z0_diff_r/4
    zdiff_vec_l = np.ones((1, n_port_diff_side)) * z0_diff_l
    zdiff_vec_r = np.ones((1, n_port_diff_side)) * z0_diff_r
    zcomm_vec_l = np.ones((1, n_port_diff_side)) * z0_comm_l
    zcomm_vec_r = np.ones((1, n_port_diff_side)) * z0_comm_r
    z_mix = np.hstack((zdiff_vec_l, zdiff_vec_r, zcomm_vec_l, zcomm_vec_r))
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))

    # 执行转换
    # print(n_diff_port)
    # print(len(z0_mix_matrix))
    # print(z0_mix_matrix)
    network.se2gmm(p=n_diff_port, z0_mm=z0_mix_matrix)

    # 处理端口名称
    port_names = network.port_names or [f"port_{i}" for i in range(1, n_ports + 1)]
    file_name = network.name
    # 根据输出模式处理结果
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
    """
    将多对单端线转换为差分模式

    参数:
        network: 原始单端网络
        line_list: 需要转换的线对列表 [line1,line2, ...]
        port_mode: 端口模式 ('inside' 或 'inline')
        z0_diff: 差分阻抗 [z0_diff_left, z0_diff_right]
        output_mode: 输出模式 ('sdd_only' 或 'full')

    返回:
        转换后的网络
    """
    enforce_nonzero_impedance(network_ori)
    network = network_ori.copy()
    n_ports = network.nports
    n_lines = n_ports // 2
    n_diff = len(line_list)
    if not network.port_names:
        print('自动填充端口名称')
        network.port_names = [f"port_{i}" for i in range(1, n_ports + 1)]
    # 强制阻抗矩阵非零


    if not line_list:
        raise ValueError("至少需要指定一对差分线")

    # 端口重排序统一为inside模式
    if port_mode == 'inline':
        port_shape = np.reshape(np.arange(n_ports), [2, n_lines])
        port_order = port_shape.T.ravel()
        network.renumber(np.arange(n_ports), port_order)
    # 差分线索引---》差分端口索引
    line_list = [i-1 for i in line_list]  # 转换为0-based索引
    diff_port_l = line_list
    diff_port_r = [i+n_lines for i in line_list]
    diff_ports = diff_port_l + diff_port_r
    print(f'转化为“inside”模式后的差分端口：{diff_ports}')

    # 两种端口重排模式，后者更适合我的思维
    # new_ports = [None]*n_ports
    # # 处理差分端口
    # for new_idx, old_idx in enumerate(diff_ports):
    #     new_ports[old_idx] = new_idx
    # # 处理剩余端口
    # next_val = len(diff_ports)
    # for i in range(len(new_ports)):
    #     if new_ports[i] is None:
    #         new_ports[i] = next_val
    #         next_val += 1
    # network.renumber(np.arange(n_ports), new_ports)  # port_name已经自动更新
    # print(f'新端口顺序：{new_ports}')
    # 新旧端口顺序的输入位置和习惯思维正好相反
    all_ports = set(range(n_ports))
    non_diff_ports = sorted(list(all_ports - set(diff_ports)))
    # 创建新的端口顺序: 差分端口在前，单端端口在后
    new_port_order = diff_ports + non_diff_ports
    network.renumber(new_port_order, np.arange(n_ports))  # port_name已经自动更新
    # print(f'新端口顺序：{new_port_order}')
    #
    # print(f'renumber后内置端口名称：')
    # print(*network.port_names, sep="\n")
    z0_diff_l, z0_diff_r = z0_diff
    # 构建阻抗矩阵
    zdiff_vec_l = np.ones((1, n_diff // 2)) * z0_diff_l
    zdiff_vec_r = np.ones((1, n_diff // 2)) * z0_diff_r
    zcomm_vec_l = np.ones((1, n_diff // 2)) * z0_diff_l / 4
    zcomm_vec_r = np.ones((1, n_diff // 2)) * z0_diff_r / 4
    z_mix = np.hstack((zdiff_vec_l, zdiff_vec_r, zcomm_vec_l, zcomm_vec_r))
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))
    # 执行差分转换，需要转化的和转化后的端口序号都在最开头
    network.se2gmm(p=n_diff, z0_mm=z0_mix_matrix)  # port_name不变
    pn = network.port_names
    print(f'se2gmm后内置端口名称：')
    print(*pn, sep="\n")
    port_name_diff = [None] * n_diff
    port_name_comm = [None] * n_diff
    for i in range(n_diff):
        port_name_diff[i] = f'diff({pn[2*i], pn[2*i+1]})'
        port_name_comm[i] = f'comm({pn[2*i], pn[2*i+1]})'  #
    pn[0:n_diff] = port_name_diff
    pn[n_diff:2*n_diff] = port_name_comm
    all_ports = set(range(n_ports))
    diff_set = set(range(n_diff))
    comm_set = set(range(n_diff, n_diff*2))
    diff_se_ports = sorted(list(all_ports - comm_set))
    n_lines_new = len(diff_se_ports)//2
    new_network = network.subnetwork(ports=diff_se_ports)  # port_name已经自动更新
    # print(f'手动修改后的端口名称：')
    # print(*new_network.port_names, sep="\n")
    ppo = list(range(n_ports-n_diff))
    # print(ppo)
    for i in range(n_diff//2):
        element = ppo.pop(n_diff//2)
        print(element)
        ppo.insert(n_lines_new+n_diff//2-1, element)
    # print(ppo)
    new_network.renumber(ppo, list(range(n_ports-n_diff)))  # port_name已经自动更新
    # print(f'subnetwork后内置端口名称：')
    # print(*new_network.port_names, sep="\n")
    suffix = f'_partial_diff{z0_diff_l:.0f}_{z0_diff_r:.0f}ohm.s{len(diff_se_ports)}p'
    new_network.name = f"{network.name.split('.')[0]}{suffix}"

    return new_network


def SE2diff_port(
        network_ori: rf.Network,
        diff_list: list,
        z0_diff=100,
        output_mode='sdd_only'
) -> rf.Network:
    """
    将多对单端线转换为差分模式
    ！！！！！！！！！！！！需增加端口名处理！！！！！！！！
    参数:
        network: 原始单端网络
        diff_list: 端口对列表 [port1, port2, port3, port4,...]
        z0_diff: 差模阻抗值（单值）
        output_mode: 输出模式 ('sdd_only' 或 'full')
!!!!!!!!!!还未对diff-list的数据进行有效提取
    返回:
        转换后的网络
    """
    enforce_nonzero_impedance(network_ori)
    # 创建副本避免修改原网络
    network = network_ori.copy()
    n_ports = network.nports


    # 验证输入
    if not diff_list:
        raise ValueError("至少需要指定一对差分端口")

    # 差分线索引---》差分端口索引
    n_diff = len(diff_list) // 2
    diff_ports = [i-1 for i in diff_list]  # 转换为0-based索引
    print(f'差分端口序号(0-base)：{diff_ports}')

    all_ports = set(range(n_ports))
    non_diff_ports = sorted(list(all_ports - set(diff_ports)))
    # 创建新的端口顺序: 差分端口在前，单端端口在后
    new_port_order = diff_ports + non_diff_ports
    network.renumber(new_port_order, np.arange(n_ports))  # port_name已经自动更新
    # 构建阻抗矩阵
    zdiff_vec = np.ones((1, n_diff)) * z0_diff
    zcomm_vec = np.ones((1, n_diff)) * z0_diff / 4
    z_mix = np.hstack((zdiff_vec, zcomm_vec))
    print(f'Zmm = {z_mix}')
    z0_mix_matrix = np.tile(z_mix, (len(network.f), 1))
    # print(z0_mix_matrix)
    # 执行差分转换，需要转化的和转化后的端口序号都在最开头
    network.se2gmm(p=n_diff, z0_mm=z0_mix_matrix)  # port_name不变

    pn = network.port_names
    port_name_diff = [None] * n_diff
    port_name_comm = [None] * n_diff
    for i in range(n_diff):
        port_name_diff[i] = f'diff({pn[2*i], pn[2*i+1]})'
        port_name_comm[i] = f'comm({pn[2*i], pn[2*i+1]})'  #
    pn[0:n_diff] = port_name_diff
    pn[n_diff:2*n_diff] = port_name_comm
    all_ports = set(range(n_ports))
    diff_set = set(range(n_diff))
    comm_set = set(range(n_diff, n_diff*2))
    diff_se_ports = sorted(list(all_ports - comm_set))
    n_lines_new = len(diff_se_ports)//2
    new_network = network.subnetwork(ports=diff_se_ports)  # port_name已经自动更新
    ppo = list(range(n_ports-n_diff))
    # print(ppo)
    for i in range(n_diff//2):
        element = ppo.pop(n_diff//2)
        print(element)
        ppo.insert(n_lines_new+n_diff//2-1, element)
    # print(ppo)
    new_network.renumber(ppo, list(range(n_ports-n_diff)))  # port_name已经自动更新
    # print(f'subnetwork后内置端口名称：')
    # print(*new_network.port_names, sep="\n")
    suffix = f'_partial_diff{z0_diff:.0f}ohm.s{len(diff_se_ports)}p'
    new_network.name = f"{network.name.split('.')[0]}{suffix}"

    return new_network
# endregion

# UI辅助函数模块


def get_network(self, file_name):
    """从缓存获取或加载 S 参数数据"""
    if file_name not in self.s_data:

        self.s_data[file_name] = rf.Network(file_name)
        enforce_nonzero_z0(self.s_data[file_name], file_name)

    return self.s_data[file_name]


def check_and_set_port_names(parent, file_list):
    """
    增强版端口检查函数，包含完整处理逻辑
    返回: 排序后的端口索引列表 (从1开始)，或None表示失败
    """
    from UI2_PortSelection import PortSelector
    from portname_setting import PortNameDialog
    # 检查文件选择
    if not file_list:
        QMessageBox.warning(parent, "警告", "请先选择S参数文件")
        return None

    if len(file_list) > 1:
        QMessageBox.information(parent, "提示", "检测到多文件选择，将使用第一个文件的端口")

    # 加载网络数据
    try:
        network = get_network(parent, file_list[0])
    except Exception as e:
        QMessageBox.critical(parent, "错误", f"文件加载失败: {str(e)}")
        return None

    # 检查/设置端口名
    if not network.port_names:
        dialog = PortNameDialog(parent, network.nports, file_list[0])
        network.port_names = dialog.get_port_names()

        if not network.port_names:  # 用户选择"不生成"或输入无效
            return None

    # 弹出端口选择器
    result, indices = PortSelector.select_ports(network.port_names, parent)
    if result != QDialog.DialogCode.Accepted or not indices:
        return None

    # 处理选择结果
    indices.sort()
    selected_names = [network.port_names[i - 1] for i in indices]

    # 打印和剪贴板操作
    print(f"\n=== 端口选择结果 ===")
    print(f"• 索引: {indices}\n• 名称: {', '.join(selected_names)}")
    QApplication.clipboard().setText(" ".join(map(str, indices)))

    return indices


def get_s(self, file_name):
    """从缓存获取或加载 S 参数数据"""
    if file_name not in self.s_param:
        try:
            self.s_param[file_name] = self.s_data[file_name].s
        except Exception as e:
            QMessageBox.warning(self, '加载错误', f"无法读取 {file_name}的S参数:\n{str(e)}")
            return None
    return self.s_param[file_name]


def get_z(self, file_name):
    """从缓存获取或加载 S 参数数据"""
    if file_name not in self.z_param:
        try:
            self.z_param[file_name] = self.s_data[file_name].z
        except Exception as e:
            QMessageBox.warning(self, '加载错误', f"无法读取 {file_name}的Z参数:\n{str(e)}")
            return None
    return self.z_param[file_name]


def get_y(self, file_name):
    """从缓存获取或加载 S 参数数据"""
    if file_name not in self.y_param:
        try:
            self.y_param[file_name] = self.s_data[file_name].y
        except Exception as e:
            QMessageBox.warning(self, '加载错误', f"无法读取 {file_name}的Y参数:\n{str(e)}")
            return None
    return self.y_param[file_name]


def validate_inputs(self):
    """验证所有输入是否有效（支持多端口解析）"""
    # 检查的位置应该在函数外，待修改
    all_ports = []

    for row in range(self.table.rowCount()):
        # 检查端口号（使用parse_port_input解析）
        port_item = self.table.item(row, 0)
        if not port_item or not port_item.text():
            QMessageBox.warning(self, "输入错误",
                                f"第 {row + 1} 行: 端口号不能为空")
            self.table.selectRow(row)
            self.table.editItem(port_item)
            return False

        # 使用parse_port_input解析输入
        parsed_ports = parse_port_input(port_item.text())
        if parsed_ports is None:  # 解析失败时已显示错误信息
            self.table.selectRow(row)
            self.table.editItem(port_item)
            return False

        # 检查端口号有效性
        for port in parsed_ports:
            if port <= 0:
                QMessageBox.warning(self, "输入错误",
                                    f"第 {row + 1} 行: 端口号必须大于0 (检测到 {port})")
                self.table.selectRow(row)
                self.table.editItem(port_item)
                return False

            if port in all_ports:
                QMessageBox.warning(self, "输入错误",
                                    f"第 {row + 1} 行: 端口号 {port} 已重复")
                self.table.selectRow(row)
                self.table.editItem(port_item)
                return False

            all_ports.append(port)

        # 检查电阻值
        impedance_item = self.table.item(row, 1)
        try:
            float(impedance_item.text())
        except ValueError:
            QMessageBox.warning(self, "输入错误",
                                f"第 {row + 1} 行: 电阻值必须是数字")
            self.table.selectRow(row)
            self.table.editItem(impedance_item)
            return False

        # 检查电容值（列2，仅当表格有此列时）
        if self.table.columnCount() > 2:
            cap_item = self.table.item(row, 2)
            try:
                c_val = float(cap_item.text())
                if c_val < 0:
                    raise ValueError("电容值不能为负数")
            except ValueError as e:
                QMessageBox.warning(self, "输入错误",
                                    f"第 {row + 1} 行: 电容值无效 ({e})")
                self.table.selectRow(row)
                self.table.editItem(cap_item)
                return False

    return True

def add_unique_filename(self, new_file_name):
    # 获取当前所有文件名
    existing_names = {self.file_list.item(i).text() for i in range(self.file_list.count())}

    # 如果文件名已存在，添加数字后缀
    base_name = new_file_name
    suffix = 1
    while new_file_name in existing_names:
        # 分离文件名和扩展名（如果有）
        if '.' in base_name:
            name_part, ext_part = base_name.rsplit('.', 1)
            new_file_name = f"{name_part}_{suffix}.{ext_part}"
        else:
            new_file_name = f"{base_name}_{suffix}"
        suffix += 1

    # 添加唯一文件名
    self.file_list.addItem(new_file_name)
    return new_file_name

def freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode="max"):
    # 存储标注信息
    mark_info = []
    worst_info = []
    for fG_mark in mark_freqGs:
        idx = np.abs(freqG - fG_mark).argmin()
        actual_freq = freqG[idx]
        actual_value = y_data[idx]
        mark_info.append({
            'freq': float(actual_freq),
            'value': float(actual_value)
        })

        # 绘制频段内的极值点
        mask = (freqG <= fG_mark)
        band_freqG = freqG[mask]
        band_data = y_data[mask]
        # 查找最大&最小值
        if worst_mode == "max":
            worst_idx = np.argmax(band_data)
            worst_freqG = band_freqG[worst_idx]
            worst_value = band_data[worst_idx]
        else:
            worst_idx = np.argmin(band_data)
            worst_freqG = band_freqG[worst_idx]
            worst_value = band_data[worst_idx]
        # 用红点标注极值
        ax.plot(worst_freqG, worst_value, 'ro', markersize=5)
        ax.plot(worst_freqG, worst_value, 'ro', markersize=5)
        # 记录最大值信息
        worst_info.append({
            'freq': float(worst_freqG),
            'value': float(worst_value)
        })
    return mark_info, worst_info


def ripple_calc(network, p1, p2, start_freqG, stop_freqG, data_mode, method, fit_params):
    """
    参数说明:
        fit_params: 字典，包含不同方法所需的参数:
            - "n次多项式": {'order': 多项式阶数}
            - "平滑函数": {'window_length': 窗长度, 'polyorder': 阶数}
            - "IEEE_std_802.3-2022": {} (无额外参数)
    """
    s_params = network.s
    freqG = network.f / 1e9  # GHz
    file_name = network.name
    s_param = s_params[:, p1 - 1, p2 - 1]  # 转换为0-based索引
    label = f'{file_name.split("/")[-1]}_S{p1},{p2}'

    # 筛选频带内的数据
    mask = (freqG >= start_freqG) & (freqG <= stop_freqG)
    freqG_range = freqG[mask]

    if data_mode == "幅度 (dB)":
        s_param_range = 20 * np.log10(np.abs(s_param[mask]))
    elif data_mode == "幅度 (abs)":
        s_param_range = np.abs(s_param[mask])
    elif data_mode == "unwrap相位 (度)":
        s_param_range = np.unwrap(np.angle(s_param[mask])) * 180 / np.pi
    elif data_mode == "unwrap相位 (rad)":
        s_param_range = np.unwrap(np.angle(s_param[mask]))  # 弧度
    else:
        raise ValueError("暂不支持该类型数据拟合")

    s_param_fit = s_param_range - s_param_range[0]

    if method == "n次多项式":
        # 多项式拟合
        coeffs = Polynomial.fit(freqG_range, s_param_fit, fit_params['order']).convert().coef
        fitted_curve = np.polyval(coeffs[::-1], freqG_range) + s_param_range[0]
    elif method == "IEEE_std_802.3-2022":
        # IEEE标准拟合
        result_fit = _ieee_8023_fit(freqG_range, s_param_fit)
        fitted_curve = result_fit['fitted_curve']
    elif method == "平滑函数":
        from scipy.signal import savgol_filter
        fitted_curve = savgol_filter(
            s_param_range,
            window_length=fit_params['window_length'],
            polyorder=fit_params['polyorder']
        )

    # 计算残差
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
        'formula': result_fit['formula'] if method == "IEEE_std_802.3-2022" else None
    }


def plot_main_curves(results_data, data_mode):
    """绘制主曲线（原始曲线和拟合曲线）"""
    plt.figure()
    if sys.platform == 'win32':
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 仅影响普通文本
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # 仅影响普通文本
    plt.rcParams['axes.unicode_minus'] = False
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
    plt.figure()
    if sys.platform == 'win32':
        plt.rcParams['font.sans-serif'] = ['SimHei']
    else:
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
    plt.rcParams['axes.unicode_minus'] = False
    for data in results_data:
        plt.plot(data['freqG_range'], data['residuals'],
                 label=f"{data['label']} (ripple)")

    plt.legend()
    plt.xlabel('频率 (GHz)')
    plt.ylabel(data_mode)
    plt.title('S参数拟合Ripple')
    plt.grid(True)
    plt.show()


def ripple_calc1(network, p1, p2, start_freqG, stop_freqG, data_mode, method, results, order):
    s_params = network.s
    freqG = network.f / 1e9  # GHz
    file_name = network.name
    s_param = s_params[:, p1 - 1, p2 - 1]  # 转换为0-based索引
    label = f'{file_name.split("/")[-1]}_S{p1},{p2}'

    # 筛选频带内的数据
    mask = (freqG >= start_freqG) & (freqG <= stop_freqG)
    freqG_range = freqG[mask]

    if data_mode == "幅度 (dB)":
        s_param_range = 20 * np.log10(np.abs(s_param[mask]))
    elif data_mode == "幅度 (abs)":
        s_param_range = np.abs(s_param[mask])
    elif data_mode == "unwrap相位 (度)":
        s_param_range = np.unwrap(np.angle(s_param[mask])) * 180 / np.pi
    elif data_mode == "unwrap相位 (rad)":
        s_param_range = np.unwrap(np.angle(s_param[mask]))  # 弧度
    else:
        print("暂不支持该类型数据拟合")

    s_param_fit = s_param_range - s_param_range[0]

    if method == "n次多项式":
        # 多项式拟合
        coeffs = Polynomial.fit(freqG_range, s_param_fit, order).convert().coef
        fitted_curve = np.polyval(coeffs[::-1], freqG_range) + s_param_range[0]
    elif method == "IEEE_std_802.3-2022":
        # IEEE标准拟合
        result_fit = _ieee_8023_fit(freqG_range, s_param_fit)
        fitted_curve = result_fit['fitted_curve']
    # 计算残差
    residuals = np.abs(s_param_range - fitted_curve)
    max_ripple = np.max(residuals)
    max_ripple_index = np.argmax(residuals)
    max_ripple_freqG = freqG_range[max_ripple_index]

    # 存储结果
    results.append(f'{label}: ripple = {max_ripple:.4f} dB')

    # 绘制原始曲线和拟合曲线
    plt.plot(freqG_range, s_param_range, label=label)
    plt.plot(freqG_range, fitted_curve, '--', label=f'{label} (拟合)')
    plt.plot(max_ripple_freqG, s_param_range[max_ripple_index], 'o')  # , label=f'{label} 最大 ripple'
    # self.write('plot')
    # 添加公式标注
    if method == "IEEE_std_802.3-2022":
        plt.annotate(
            result_fit['formula'],
            xy=(0.5, 0.95), xycoords='axes fraction',
            ha='center', va='top',
            bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3)
        )
    return results


def _ieee_8023_fit(freqG, s_param_db):
    """
    IEEE 802.3-2022 标准拟合公式实现
    公式: IL(f) = a0 + a1*sqrt(f) + a2*f + a4*f^2
    """
    freq = freqG * 1e9  # 转换为Hz

    # 构造设计矩阵
    X = np.column_stack([
        np.ones_like(freq),
        np.sqrt(freq),
        freq,
        freq ** 2
    ])

    # 最小二乘法求解系数
    coeffs, _, _, _ = np.linalg.lstsq(X, s_param_db, rcond=None)

    # 生成拟合曲线
    fitted = (coeffs[0] +
              coeffs[1] * np.sqrt(freq) +
              coeffs[2] * freq +
              coeffs[3] * freq ** 2)
    # return fitted

    return {
        'fitted_curve': fitted,
        'coeffs': {
            'a0': coeffs[0],
            'a1': coeffs[1],
            'a2': coeffs[2],
            'a4': coeffs[3]
        },
        'formula': "IL(f) = {a0:.3f} + {a1:.3g}*√f + {a2:.3g}*f + {a4:.3g}*f^2".format(
            a0=coeffs[0], a1=coeffs[1], a2=coeffs[2], a4=coeffs[3])
    }


def parse_port_input1(input_str):
    """解析端口输入，支持格式如 1:5、1:2:5、[1,2,5]、[1，2，5]、[1 2 5] 或 1 2 5

    参数:
        input_str (str): 用户输入的端口字符串

    返回:
        list: 解析后的端口列表，如果解析失败则返回None
    """
    try:
        # 去除首尾空格和方括号
        cleaned = input_str.strip().strip('[]')

        if ':' in cleaned:
            # 处理 1:5 或 1:2:5 格式
            parts = []
            for part in cleaned.split(':'):
                parts.extend(part.strip().split())  # 处理可能存在的空格
            parts = list(map(int, parts))

            if len(parts) == 2:
                return list(range(parts[0], parts[1] + 1))
            elif len(parts) == 3:
                return list(range(parts[0], parts[2] + 1, parts[1]))
            else:
                raise ValueError("冒号格式不正确")
        else:
            # 将中文逗号替换为英文逗号
            cleaned = cleaned.replace('，', ',')

            # 处理逗号或空格分隔的列表
            if ',' in cleaned:
                # 分割后去除每个元素两端的空格
                return [int(num.strip()) for num in cleaned.split(',') if num.strip()]
            else:
                # 处理空格分隔的数字
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


from PyQt6.QtWidgets import QMessageBox


def parse_port_input(input_str, type='port'):
    """解析端口或频率输入，支持多种格式如 1:5、1:2:5、[1,2,5]、[1，2，5]、[1 2 5] 或 1 2 5

    参数:
        input_str (str): 用户输入的字符串
        type (str): 输入类型，'port' 表示端口（只支持整数），'freq' 表示频率（支持小数）

    返回:
        list: 解析后的列表（整数或小数），失败时返回 None
    """
    try:
        # 去除首尾空格和方括号
        cleaned = input_str.strip().strip('[]')
        # 替换中文逗号和中文冒号为英文
        cleaned = cleaned.replace('，', ',').replace('：', ':')

        # 设置转换函数：根据 type 选择 int 或 float
        convert = float if type == 'freq' else int

        if ':' in cleaned:
            parts = []
            for part in cleaned.split(':'):
                parts.extend(part.strip().split())  # 处理可能存在的空格
            parts = list(map(convert, parts))

            if len(parts) == 2:
                start, end = parts
                step = 1.0 if type == 'freq' else 1
            elif len(parts) == 3:
                start, step, end = parts
            else:
                raise ValueError("冒号格式不正确")

            # 生成序列：频率支持小数步进
            if type == 'freq':
                result = []
                current = start
                while (step > 0 and current <= end) or (step < 0 and current >= end):
                    result.append(round(current, 10))  # 控制精度，避免浮点误差
                    current += step
                return result
            else:
                return list(range(int(start), int(end) + 1, int(step)))

        else:
            # 使用逗号或空格分隔的形式
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


def show_error(parent, context_message=""):
    """显示带行号的错误弹窗"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    last_frame = traceback.extract_tb(exc_traceback)[-1]

    error_msg = f"""
    {context_message}

    🛑 错误位置: 
    文件: {last_frame.filename}
    行号: {last_frame.lineno}
    函数: {last_frame.name}

    💥 错误详情: 
    {str(exc_value)}
    """
    QMessageBox.critical(parent, '错误', error_msg)


def resource_path(relative_path):
    """ 获取资源的绝对路径，适用于开发环境和PyInstaller打包环境 """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 普通开发环境
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# 模块终点
