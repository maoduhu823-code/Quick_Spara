"""拓扑识别 — 用低频 Y 矩阵的相对关系识别 1 驱 1 / 1 驱多端口对。

判别只用单个低频点：S → Y 后比较 |Y_ij|。
- 1 驱多（multi-drop）：以"被多个端口共同视作最强对端"的节点为 driver，
  并要求 driver 自身的前 N 强对端覆盖这些追随者（双向验证，N = 追随者数）；
- 1 驱 1（p2p）：剩余端口里互为最强的端口对；
- 既没进入簇也没进入对的端口归为孤立端口。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import skrf as rf


# ============================================================
# 数据类
# ============================================================

@dataclass
class ChannelInfo:
    """一条联通通道。

    S 参数互易（S_ij = S_ji），无法从矩阵判断信号方向；这里的 `tx` 仅表示
    "拓扑中心"（T 型节点 / 星型 hub），不是物理 driver。p2p 时 `tx` 取低序号端口。
    """
    ports: List[int]              # 1-based 端口号，含中心节点与全部分支节点
    tx: Optional[int] = None      # 拓扑中心节点（1-based）；p2p 时为低序号端口
    rxs: List[int] = field(default_factory=list)  # 其余分支节点（1-based，按端口号升序）
    s_value: Optional[complex] = None             # rx_s_values[0]，留作 p2p 后向兼容
    z_value: Optional[complex] = None             # rx_z_values[0]
    rx_s_values: List[complex] = field(default_factory=list)  # 与 rxs 一一对应
    rx_z_values: List[complex] = field(default_factory=list)
    delays_ns: List[float] = field(default_factory=list)
    il_db: List[float] = field(default_factory=list)
    topology: str = "p2p"          # "p2p" | "multi-drop"


@dataclass
class TopologyReport:
    n_ports: int
    band_ghz: Tuple[float, float]       # 兼容旧报告结构，本版不使用 mid-band
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


def _greedy_cluster(
    y_abs: np.ndarray,
    fanout_tol: float = 0.5,
) -> List[Tuple[int, List[int]]]:
    """识别 0-based 联通簇。

    返回 [(driver, sorted([rx, ...])), ...]，每个端口至多出现在一个簇里。
    - len(rxs) == 1：传统 p2p 互为最强对；driver 取 (min(i,j))。
    - len(rxs) >= 2：1 驱多；driver 是被多个端口共同视作最强对端的 hub，
      且 hub 的前 N 强对端与这些追随者重叠数 ≥ ceil(fanout_tol·N)。
    """
    n = y_abs.shape[0]
    if n < 2:
        return []

    score = y_abs.copy()
    np.fill_diagonal(score, -np.inf)
    best = np.argmax(score, axis=1)
    best_strength = score[np.arange(n), best]

    # 反向汇集：driver 候选 -> 视其为最强对端的端口列表
    incoming: Dict[int, List[int]] = {}
    for j in range(n):
        if not np.isfinite(best_strength[j]) or best_strength[j] <= 0:
            continue
        d = int(best[j])
        incoming.setdefault(d, []).append(j)

    used: set[int] = set()
    clusters: List[Tuple[int, List[int]]] = []

    # 第一遍：识别 fan-out ≥ 2 的 1 驱多
    for d in sorted(incoming, key=lambda x: (-len(incoming[x]), x)):
        if d in used:
            continue
        rxs = [r for r in incoming[d] if r not in used and r != d]
        if len(rxs) < 2:
            continue
        # 双向验证：d 自身的前 N 强对端要与 rxs 显著重叠
        d_row = y_abs[d].copy()
        d_row[d] = -np.inf
        n_top = len(rxs)
        d_top_idx = np.argpartition(d_row, -n_top)[-n_top:]
        d_top_set = {int(x) for x in d_top_idx if y_abs[d, int(x)] > 0}
        kept = sorted(set(rxs) & d_top_set)
        min_required = max(2, int(np.ceil(fanout_tol * n_top)))
        if len(kept) >= min_required:
            clusters.append((d, kept))
            used.add(d)
            used.update(kept)

    # 第二遍：剩余端口做 p2p 互为最强
    pairs: set[Tuple[int, int]] = set()
    for i in range(n):
        if i in used:
            continue
        if not np.isfinite(best_strength[i]) or best_strength[i] <= 0:
            continue
        j = int(best[i])
        if j == i or j in used:
            continue
        if int(best[j]) == i and best_strength[j] > 0:
            pairs.add(tuple(sorted((i, j))))  # type: ignore[arg-type]
    for lo, hi in sorted(pairs):
        if lo in used or hi in used:
            continue
        clusters.append((lo, [hi]))
        used.add(lo)
        used.add(hi)

    return clusters


def _format_s_db(value: Optional[complex]) -> str:
    if value is None:
        return "N/A"
    mag = abs(complex(value))
    with np.errstate(divide='ignore'):
        db = 20.0 * np.log10(mag)
    return f"{db:.2f} dB"


def _format_abs(value: Optional[complex], unit: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{abs(complex(value)):.4g}{unit}"


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
    fanout_tol: float = 0.5,
) -> TopologyReport:
    """推断端口联通关系（1 驱 1 / 1 驱多）。

    `band_ghz`、`y_threshold_siemens`、`s_threshold_db`、`delay_tolerance_ns`
    保留为兼容参数，本版不参与判别。`fanout_tol` 控制 1 驱多双向验证的宽松度。
    """
    _ = (band_ghz, y_threshold_siemens, s_threshold_db, delay_tolerance_ns)
    n = network.nports
    freq = network.f
    if n < 2:
        return TopologyReport(
            n_ports=n, band_ghz=(0.0, 0.0), low_freq_ghz=0.0,
            y_threshold_siemens=y_threshold_siemens,
            s_threshold_db=s_threshold_db,
            channels=[], isolated_ports=list(range(1, n + 1)),
        )

    target_hz = low_freq_ghz * 1e9
    low_idx = int(np.abs(freq - target_hz).argmin())
    low_used_ghz = float(freq[low_idx] / 1e9)
    z0_at_low = np.real(np.asarray(network.z0[low_idx]))
    y_mat = _s_to_y(network.s[low_idx], z0_at_low)
    y_abs = np.abs(y_mat)
    np.fill_diagonal(y_abs, 0.0)
    s_mat = network.s[low_idx]
    try:
        z_mat = network.z[low_idx]
    except Exception:
        z_mat = None

    clusters = _greedy_cluster(y_abs, fanout_tol=fanout_tol)
    paired_ports: set[int] = set()
    channels: List[ChannelInfo] = []
    for d_idx, rx_idxs in clusters:
        tx_port = d_idx + 1
        rx_ports = [r + 1 for r in rx_idxs]
        paired_ports.add(tx_port)
        paired_ports.update(rx_ports)
        rx_s = [complex(s_mat[d_idx, r]) for r in rx_idxs]
        rx_z = (
            [complex(z_mat[d_idx, r]) for r in rx_idxs]
            if z_mat is not None else []
        )
        topo = "p2p" if len(rx_ports) == 1 else "multi-drop"
        channels.append(ChannelInfo(
            ports=[tx_port] + rx_ports,
            tx=tx_port,
            rxs=rx_ports,
            s_value=rx_s[0] if rx_s else None,
            z_value=rx_z[0] if rx_z else None,
            rx_s_values=rx_s,
            rx_z_values=rx_z,
            topology=topo,
        ))
    isolated = [p for p in range(1, n + 1) if p not in paired_ports]

    return TopologyReport(
        n_ports=n,
        band_ghz=(0.0, 0.0),
        low_freq_ghz=low_used_ghz,
        y_threshold_siemens=y_threshold_siemens,
        s_threshold_db=s_threshold_db,
        channels=channels,
        isolated_ports=isolated,
    )


def format_report(report: TopologyReport, file_label: str = "") -> str:
    """把 TopologyReport 渲染成可读文本，供主窗口控制台输出。

    当前面向 SI 链路场景：只显示 S 参数耦合；Z 仍保留在 ChannelInfo 里，PI
    场景后续按需切换。联通簇用 `[port a, port b*, ...]` 列出全部成员，
    `*` 标记拓扑中心节点（T 型 / 星型分支点，不代表信号方向）。
    """
    lines: List[str] = []
    head = "=== 拓扑识别"
    if file_label:
        head += f"：{file_label}"
    head += " ==="
    lines.append(head)
    lines.append(
        f"端口数 = {report.n_ports}，"
        f"低频探测点 = {report.low_freq_ghz:.4f} GHz："
    )
    if not report.channels:
        lines.append("未识别到任何耦合端口对。")
    for idx, ch in enumerate(report.channels, start=1):
        all_ports = sorted(set(ch.ports))
        members = ", ".join(
            f"port {p}*" if p == ch.tx else f"port {p}"
            for p in all_ports
        )
        if ch.topology == "multi-drop" and ch.tx is not None:
            s_parts = ", ".join(
                f"S{ch.tx},{r}={_format_s_db(sv)}"
                for r, sv in zip(ch.rxs, ch.rx_s_values)
            )
            lines.append(
                f"联通簇 {idx}（{len(all_ports)} 端口）: "
                f"[{members}]  耦合: {s_parts}; "
            )
            continue

        rx = ch.rxs[0] if ch.rxs else None
        if rx is not None:
            lines.append(
                f"联通端口对 {idx}: [{members}]  "
                f"耦合: S{ch.tx},{rx}={_format_s_db(ch.s_value)}"
            )
    if report.isolated_ports:
        lines.append(
            "孤立端口（未与任何端口形成显著耦合）：" +
            ", ".join(str(p) for p in report.isolated_ports)
        )
    return "\n".join(lines)
