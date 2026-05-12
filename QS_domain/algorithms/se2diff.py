"""单端 → 差分/混合模式 S 参数转换算法。"""

import numpy as np
import skrf as rf

from QS_domain.algorithms.impedance import has_zero_impedance


def _require_nonzero_z0(network: rf.Network) -> None:
    """阻抗为零时抛出 ValueError，让调用方在 UI 层先行修正。"""
    if has_zero_impedance(network):
        raise ValueError(
            "网络端口阻抗存在零值，请先通过[修改参考阻抗]设置有效 Z0 后再执行转换。"
        )


def SE2diff(
        network_ori: rf.Network,
        port_mode: str = 'inside',
        output_mode: str = 'sdd_only',
        z0_diff: list = None,
) -> rf.Network:
    """将单端S参数转换为差分/混合模式。"""
    if z0_diff is None:
        z0_diff = [100, 100]

    _require_nonzero_z0(network_ori)
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
        port_mode: str = 'inside',
        z0_diff: list = None,
) -> rf.Network:
    """将多对单端线转换为差分模式（线逻辑）。"""
    if z0_diff is None:
        z0_diff = [100, 100]

    _require_nonzero_z0(network_ori)
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
    print('se2gmm后内置端口名称：')
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
        z0_diff: float = 100,
        output_mode: str = 'sdd_only',
) -> rf.Network:
    """将多对单端线转换为差分模式（端口逻辑）。"""
    _require_nonzero_z0(network_ori)
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
