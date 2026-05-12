"""
端口阻抗检查与修正 — 纯函数层，无 Qt 依赖。

UI 层负责弹窗询问用户，然后调用 replace_zero_impedance()。
enforce_nonzero_impedance() 作为向后兼容别名保留在 sparam_core.py。
"""

import numpy as np
import skrf as rf


def has_zero_impedance(network: rf.Network) -> bool:
    """检查网络是否存在零阻抗端口。"""
    return bool(np.any(np.array(network.z0) == 0))


def replace_zero_impedance(network: rf.Network, z0: float) -> None:
    """将网络所有端口阻抗替换为指定值。"""
    if z0 <= 0:
        raise ValueError(f"阻抗值必须为正数，收到: {z0}")
    n_ports = network.nports
    network.z0 = np.ones((len(network.f), n_ports)) * z0
    print(f"已将全部端口阻抗设置为 {z0}Ω")


def enforce_nonzero_z0(network_ori: rf.Network, filepath: str) -> None:
    """检查并处理阻抗矩阵中的零值，从文件头行读取参考阻抗直接修正。"""
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
