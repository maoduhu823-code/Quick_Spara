import skrf as rf
import numpy as np

# ── 配置区 ──────────────────────────────────────────────────────────────────
INPUT_FILE   = 'C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p'
OUTPUT_FILE  = './port_merge_out.s3p'   # 输出文件名后缀需与结果端口数匹配
MERGE_PORTS  = [0, 1]    # 要并联的端口索引（0-based），其余端口保留
# ────────────────────────────────────────────────────────────────────────────


def merge_ports(ntw: rf.Network, merge_idx: list[int]) -> rf.Network:
    """
    将 ntw 中 merge_idx 指定的 m 个端口并联合并为 1 个端口。

    合并规则（Y 矩阵法）：
        Y_AA      = Σ Y[i,j]   for i,j ∈ merge_idx
        Y_Ak/Y_kA = Σ Y[i,k]  for i ∈ merge_idx, k ∈ keep_idx
        Y_kl      = 不变       for k,l ∈ keep_idx

    返回：新的 (n - m + 1) 端口 Network，参考阻抗取 merge_idx[0] 的 z0。
    """
    n = ntw.nports
    merge_idx = list(merge_idx)
    keep_idx  = [p for p in range(n) if p not in merge_idx]
    n_new     = len(keep_idx) + 1          # 合并后端口数
    nf        = len(ntw.frequency)

    y_orig = ntw.y                         # shape: (f, n, n)
    y_new  = np.zeros((nf, n_new, n_new), dtype=complex)

    # 行/列 0 = 新合并端口 A；行/列 1..n_new-1 = 保留端口（顺序不变）

    # Y_AA
    y_new[:, 0, 0] = y_orig[:, np.ix_(merge_idx, merge_idx)[0],
                                np.ix_(merge_idx, merge_idx)[1]].sum(axis=(1, 2))

    # Y_Ak 和 Y_kA
    for col_new, k in enumerate(keep_idx, start=1):
        y_new[:, 0, col_new] = y_orig[:, merge_idx, k].sum(axis=1)   # Y_Ak
        y_new[:, col_new, 0] = y_orig[:, k, merge_idx].sum(axis=1)   # Y_kA

    # Y_kl（保留端口间，原值不变）
    for row_new, k in enumerate(keep_idx, start=1):
        for col_new, l in enumerate(keep_idx, start=1):
            y_new[:, row_new, col_new] = y_orig[:, k, l]

    # 参考阻抗：合并端口取 merge_idx[0] 的 z0，保留端口取各自原 z0
    z0_merge = ntw.z0[:, merge_idx[0]]
    z0_kept  = ntw.z0[:, keep_idx]                        # shape (f, len(keep_idx))
    z0_new   = np.hstack([z0_merge[:, np.newaxis], z0_kept])  # shape (f, n_new)

    return rf.Network(frequency=ntw.frequency, y=y_new, z0=z0_new)


# ── 主流程 ───────────────────────────────────────────────────────────────────
ntw = rf.Network(INPUT_FILE)
print(f"原始网络：{ntw.nports} 端口，{len(ntw.frequency)} 个频点")
print(f"合并端口索引：{MERGE_PORTS}  →  剩余端口数：{ntw.nports - len(MERGE_PORTS) + 1}")

ntw_merged = merge_ports(ntw, MERGE_PORTS)
ntw_merged.write_touchstone(OUTPUT_FILE)
print(f"完成，结果已保存至：{OUTPUT_FILE}")
