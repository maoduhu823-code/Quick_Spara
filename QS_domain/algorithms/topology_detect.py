"""
拓扑识别 — 从 N 端口 S 参数推断 TX↔RX 的配对关系。

核心思路（详见 docs/AGENT_GUIDE.md / 反馈讨论）：
  1. 在低频段把 S → Y，用 |Y_ij| 阈值化得到"物理连通图"，做并查集划分独立链路。
     —— 低频时电路连通性比 mid-band 的 |S21| 更稳，远端 drop 的 IL 大也不会被漏判。
  2. 每条链路内：
       - 节点数 = 2：1 驱 1，直接配对；
       - 节点数 > 2：用 mid-band |S_ji| 行和找 hub（驱动端），其余为接收端；
                    用群延迟（mid-band 上 ∠S 对 ω 的斜率）排序 RX 推断 multi-drop 顺序。
  3. 区分 star / multi-drop：检查 RX 之间的三角不等式
     |τ(TX→RX_i) − τ(TX→RX_j)|  ≈  τ(RX_i→RX_j)
       - 接近成立 → multi-drop（在同一 trunk 上）
       - 偏差大 → star / 独立分支

本模块纯函数、无 Qt 依赖。UI 层负责把结果格式化为文本/图。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import skrf as rf


# ============================================================
# 数据类
# ============================================================

@dataclass
class ChannelInfo:
    """一条独立链路（一个连通分量）。"""
    ports: List[int]              # 1-based 端口号
    tx: Optional[int] = None      # 1-based；None 表示无法判定
    rxs: List[int] = field(default_factory=list)  # 1-based，按群延迟从近到远
    delays_ns: List[float] = field(default_factory=list)  # 与 rxs 一一对应，TX→RX_k 的群延迟
    il_db: List[float] = field(default_factory=list)      # 与 rxs 一一对应，mid-band 平均 |S| 的 dB
    topology: str = "unknown"     # "p2p" / "star" / "multi-drop" / "unknown"


@dataclass
class TopologyReport:
    n_ports: int
    band_ghz: Tuple[float, float]       # 实际使用的 mid-band
    low_freq_ghz: float                  # 用于 Y 矩阵连通性的低频
    y_threshold_siemens: float
    s_threshold_db: float
    channels: List[ChannelInfo]
    isolated_ports: List[int]            # 没有进入任何链路的孤立端口（1-based）


# ============================================================
# 工具函数
# ============================================================

def _s_to_y(s_slice: np.ndarray, z0: np.ndarray) -> np.ndarray:
    """单频点 S → Y。s_slice (N,N), z0 (N,) 实数。返回 Y (N,N)。

    Y = sqrt(Y0) (I − S)(I + S)^{-1} sqrt(Y0)，使用归一化阻抗。
    """
    n = s_slice.shape[0]
    y0 = 1.0 / np.asarray(z0, dtype=float)
    sqrt_y0 = np.diag(np.sqrt(y0))
    eye = np.eye(n, dtype=complex)
    # 用 solve 而非 inv，避免奇异时数值崩溃
    try:
        inv_part = np.linalg.solve(eye + s_slice, eye - s_slice)
    except np.linalg.LinAlgError:
        inv_part = np.linalg.pinv(eye + s_slice) @ (eye - s_slice)
    return sqrt_y0 @ inv_part @ sqrt_y0


def _connected_components(adj: np.ndarray) -> List[List[int]]:
    """无向邻接矩阵 → 连通分量（0-based 索引）。BFS 实现。"""
    n = adj.shape[0]
    visited = np.zeros(n, dtype=bool)
    comps: List[List[int]] = []
    for start in range(n):
        if visited[start]:
            continue
        queue = [start]
        visited[start] = True
        comp = []
        while queue:
            v = queue.pop(0)
            comp.append(v)
            for u in np.where(adj[v])[0]:
                if not visited[u]:
                    visited[u] = True
                    queue.append(int(u))
        comps.append(sorted(comp))
    return comps


def _group_delay_ns(network: rf.Network, i: int, j: int,
                    f_lo_hz: float, f_hi_hz: float) -> float:
    """带内平均群延迟（ns），i/j 为 0-based。返回 NaN 表示无可用频点。

    用线性回归拟合 unwrap(∠S_ji) vs 2πf：斜率 = −τ_g。
    """
    f = network.f
    s = network.s[:, i, j]
    mask = (f >= f_lo_hz) & (f <= f_hi_hz)
    if mask.sum() < 4:
        return float('nan')
    omega = 2 * np.pi * f[mask]
    phase = np.unwrap(np.angle(s[mask]))
    # 最小二乘 phase = a + b * omega → τ = −b
    slope = np.polyfit(omega, phase, 1)[0]
    return float(-slope * 1e9)  # s → ns


# ============================================================
# 主入口
# ============================================================

def detect_topology(
    network: rf.Network,
    low_freq_ghz: float = 0.1,
    band_ghz: Optional[Tuple[float, float]] = None,
    y_threshold_siemens: float = 5e-4,
    s_threshold_db: float = -25.0,
    delay_tolerance_ns: float = 0.1,
) -> TopologyReport:
    """
    推断 N 端口网络的 TX↔RX 配对。

    Parameters
    ----------
    network : skrf.Network
        待分析的 N 端口网络。
    low_freq_ghz : float
        用于"低频 Y 矩阵连通性"的频点（GHz）。取实际频率轴上 ≥ 该值的最低频点；
        若全部频点都低于它，则取最低频点。
    band_ghz : (float, float) | None
        mid-band 起止（GHz），用于 |S| 行和找 hub、群延迟。None 表示自动取频率范围
        的 [10%, 60%] 区间。
    y_threshold_siemens : float
        |Y_ij| 超过该阈值视为"物理连通"。默认 5e-4 ≈ 1/2kΩ；50Ω 系统中典型走线
        的低频互导大致 1/50 Ω = 0.02 S 量级，远大于该阈值。
    s_threshold_db : float
        mid-band 平均 |S_ji|_dB 超过该值视为"显著耦合"（用于交叉验证 / 兜底）。
    delay_tolerance_ns : float
        判定 multi-drop 的三角不等式容差（ns）。

    Returns
    -------
    TopologyReport
    """
    n = network.nports
    freq = network.f
    if n < 2:
        return TopologyReport(
            n_ports=n, band_ghz=(0.0, 0.0), low_freq_ghz=0.0,
            y_threshold_siemens=y_threshold_siemens,
            s_threshold_db=s_threshold_db,
            channels=[], isolated_ports=list(range(1, n + 1)),
        )

    # --- 1. 自动 mid-band ---
    f_min, f_max = float(freq.min()), float(freq.max())
    if band_ghz is None:
        span = f_max - f_min
        f_lo = f_min + 0.10 * span
        f_hi = f_min + 0.60 * span
    else:
        f_lo = band_ghz[0] * 1e9
        f_hi = band_ghz[1] * 1e9
        # 越界裁剪到 [f_min, f_max]
        f_lo = max(f_min, min(f_lo, f_max))
        f_hi = max(f_min, min(f_hi, f_max))
        if f_hi <= f_lo:
            # fallback：用全频段
            f_lo, f_hi = f_min, f_max
    band_used = (f_lo / 1e9, f_hi / 1e9)

    # --- 2. 低频 Y 连通性 ---
    target_hz = low_freq_ghz * 1e9
    candidates = np.where(freq >= target_hz)[0]
    low_idx = int(candidates[0]) if candidates.size > 0 else 0
    low_used_ghz = float(freq[low_idx] / 1e9)
    z0_at_low = np.real(np.asarray(network.z0[low_idx]))
    y_mat = _s_to_y(network.s[low_idx], z0_at_low)
    y_abs = np.abs(y_mat)
    np.fill_diagonal(y_abs, 0.0)

    # --- 3. mid-band |S| 平均（dB）---
    band_mask = (freq >= f_lo) & (freq <= f_hi)
    if band_mask.sum() == 0:
        band_mask = np.ones_like(freq, dtype=bool)
    s_abs_avg = np.mean(np.abs(network.s[band_mask]), axis=0)
    np.fill_diagonal(s_abs_avg, 0.0)
    with np.errstate(divide='ignore'):
        s_db_avg = 20 * np.log10(s_abs_avg + 1e-20)

    # --- 4. 邻接：Y 阈值 OR S 阈值（两个证据都给） ---
    adj_y = y_abs > y_threshold_siemens
    adj_s = s_db_avg > s_threshold_db
    adj = (adj_y | adj_s)
    # 对称化（数值误差 / 弱不对称的容错）
    adj = adj | adj.T
    np.fill_diagonal(adj, False)

    # --- 5. 连通分量 ---
    comps = _connected_components(adj)

    channels: List[ChannelInfo] = []
    isolated: List[int] = []

    for comp in comps:
        if len(comp) == 1:
            isolated.append(comp[0] + 1)
            continue

        ports_1based = [p + 1 for p in comp]
        ch = ChannelInfo(ports=ports_1based)

        if len(comp) == 2:
            # 一驱一：TX/RX 无法仅从对称 S 区分，按端口序号约定 tx=小者
            i, j = comp
            ch.tx = i + 1
            ch.rxs = [j + 1]
            ch.delays_ns = [_group_delay_ns(network, j, i, f_lo, f_hi)]
            ch.il_db = [float(s_db_avg[i, j])]
            ch.topology = "p2p"
            channels.append(ch)
            continue

        # 一驱多：hub = 行和最大者（行和 = 该端口对子图内其他端口的 |S| 累加）
        sub_s = s_abs_avg[np.ix_(comp, comp)]
        row_sums = sub_s.sum(axis=1)  # 对角已置零
        hub_local = int(np.argmax(row_sums))
        tx_global = comp[hub_local]
        rx_globals = [p for p in comp if p != tx_global]

        # 群延迟排序
        delays = [_group_delay_ns(network, rx, tx_global, f_lo, f_hi) for rx in rx_globals]
        # NaN 排到最后
        order = sorted(range(len(rx_globals)),
                       key=lambda k: (np.isnan(delays[k]), delays[k]))
        rx_sorted = [rx_globals[k] for k in order]
        delays_sorted = [delays[k] for k in order]
        il_sorted = [float(s_db_avg[tx_global, rx]) for rx in rx_sorted]

        # 判别 star vs multi-drop：检查相邻 RX 的三角不等式
        # 对所有 RX_i, RX_j 看 |τ_i - τ_j| ≈ τ(RX_i→RX_j)
        multidrop_evidence = 0
        star_evidence = 0
        for a in range(len(rx_sorted)):
            for b in range(a + 1, len(rx_sorted)):
                ra, rb = rx_sorted[a], rx_sorted[b]
                tau_a, tau_b = delays_sorted[a], delays_sorted[b]
                if np.isnan(tau_a) or np.isnan(tau_b):
                    continue
                tau_ab = _group_delay_ns(network, ra, rb, f_lo, f_hi)
                if np.isnan(tau_ab):
                    continue
                diff = abs(abs(tau_a - tau_b) - abs(tau_ab))
                if diff < delay_tolerance_ns:
                    multidrop_evidence += 1
                else:
                    star_evidence += 1

        if multidrop_evidence > star_evidence and multidrop_evidence > 0:
            topo = "multi-drop"
        elif star_evidence > 0:
            topo = "star"
        else:
            topo = "unknown"

        ch.tx = tx_global + 1
        ch.rxs = [r + 1 for r in rx_sorted]
        ch.delays_ns = delays_sorted
        ch.il_db = il_sorted
        ch.topology = topo
        channels.append(ch)

    return TopologyReport(
        n_ports=n,
        band_ghz=band_used,
        low_freq_ghz=low_used_ghz,
        y_threshold_siemens=y_threshold_siemens,
        s_threshold_db=s_threshold_db,
        channels=channels,
        isolated_ports=isolated,
    )


def format_report(report: TopologyReport, file_label: str = "") -> str:
    """把 TopologyReport 渲染成可读文本，供主窗口控制台输出。"""
    lines: List[str] = []
    head = f"=== 拓扑识别"
    if file_label:
        head += f"：{file_label}"
    head += " ==="
    lines.append(head)
    lines.append(
        f"端口数 = {report.n_ports}，"
        f"低频探测点 = {report.low_freq_ghz:.4f} GHz（Y 阈 {report.y_threshold_siemens:g} S），"
        f"mid-band = {report.band_ghz[0]:.3f} ~ {report.band_ghz[1]:.3f} GHz"
        f"（S 阈 {report.s_threshold_db:.1f} dB）"
    )
    if not report.channels:
        lines.append("未识别到任何耦合端口对。")
    for idx, ch in enumerate(report.channels, start=1):
        if ch.topology == "p2p":
            rx = ch.rxs[0]
            tau = ch.delays_ns[0]
            il = ch.il_db[0]
            tau_s = f"{tau:.3f} ns" if not np.isnan(tau) else "N/A"
            lines.append(
                f"Channel {idx} [point-to-point]: port {ch.tx} ↔ port {rx}  "
                f"(IL≈{il:.2f} dB, τ_g≈{tau_s})"
            )
        else:
            lines.append(
                f"Channel {idx} [{ch.topology}]: hub = port {ch.tx}, "
                f"drops ({len(ch.rxs)}):"
            )
            for rx, tau, il in zip(ch.rxs, ch.delays_ns, ch.il_db):
                tau_s = f"{tau:.3f} ns" if not np.isnan(tau) else "N/A"
                lines.append(f"    port {ch.tx} → port {rx}   IL≈{il:6.2f} dB,  τ_g≈{tau_s}")
    if report.isolated_ports:
        lines.append(
            "孤立端口（未与任何端口形成显著耦合）：" +
            ", ".join(str(p) for p in report.isolated_ports)
        )
    return "\n".join(lines)
