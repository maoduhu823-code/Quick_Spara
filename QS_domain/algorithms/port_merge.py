"""端口并联合并算法（无 UI 依赖）。"""

import numpy as np
import skrf as rf


def merge_ports_multi(
        ntw: rf.Network,
        merge_groups: list,
        z0_list: list,
        y_orig: np.ndarray = None,
) -> rf.Network:
    """
    将 ntw 中多个端口组分别并联合并为单个端口，返回新网络。

    merge_groups : list[list[int]]  0-based 端口索引列表，每个子列表是一个合并组
    z0_list      : list[float]      每个合并组对应的新端口参考阻抗

    输出端口顺序：保留端口（原序）在前，合并新端口在后。
    合并新端口命名：Merge_port_<1-based索引用_分隔>
    """
    n = ntw.nports
    nf = len(ntw.frequency)

    all_merged = {p for g in merge_groups for p in g}
    keep_idx = [p for p in range(n) if p not in all_merged]
    nk = len(keep_idx)
    ng = len(merge_groups)
    n_new = nk + ng

    if y_orig is None:
        y_orig = ntw.y                                      # (nf, n, n)
    y_new = np.zeros((nf, n_new, n_new), dtype=complex)

    if keep_idx:
        y_new[:, :nk, :nk] = y_orig[np.ix_(range(nf), keep_idx, keep_idx)]

    for gi, group in enumerate(merge_groups):
        col = nk + gi
        if keep_idx:
            y_new[:, :nk, col] = y_orig[:, keep_idx, :][:, :, group].sum(axis=2)
            y_new[:, col, :nk] = y_orig[:, group, :][:, :, keep_idx].sum(axis=1)
        for gj, group_j in enumerate(merge_groups):
            row = nk + gi
            c = nk + gj
            y_new[:, row, c] = y_orig[np.ix_(range(nf), group, group_j)].sum(axis=(1, 2))

    z0_keep = ntw.z0[:, keep_idx] if keep_idx else np.empty((nf, 0))
    z0_merged = np.tile(np.array(z0_list, dtype=float), (nf, 1))
    z0_new = np.hstack([z0_keep, z0_merged])

    new_ntw = rf.Network(frequency=ntw.frequency, y=y_new, z0=z0_new)

    orig_names = ntw.port_names or [str(i + 1) for i in range(n)]
    keep_names = [orig_names[i] for i in keep_idx]
    merge_names = ["Merge_port_" + "_".join(str(p + 1) for p in g) for g in merge_groups]
    new_ntw.port_names = keep_names + merge_names

    return new_ntw
