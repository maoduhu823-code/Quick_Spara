"""拓扑识别 — 用低频 Y 矩阵的相对关系识别 1 驱 1 端口对。

本版只处理 1 驱 1 场景：在低频点把 S 转为 Y 后，每个端口选择
|Y_ij| 最大的另一端口；只有互为最强关系的端口才输出为联通端口对。
不再使用固定 S 参数 dB 阈值，也不再判别 star / multi-drop。
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
    """一条 1 驱 1 联通端口对。"""
    ports: List[int]              # 1-based 端口号
    tx: Optional[int] = None      # 低序号端口
    rxs: List[int] = field(default_factory=list)  # 仅包含高序号端口
    s_value: Optional[complex] = None             # 识别频点上的 S(低序号, 高序号)
    z_value: Optional[complex] = None             # 识别频点上的 Z(低序号, 高序号)
    delays_ns: List[float] = field(default_factory=list)
    il_db: List[float] = field(default_factory=list)
    topology: str = "p2p"


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


def _mutual_strongest_pairs(y_abs: np.ndarray) -> List[Tuple[int, int]]:
    """用低频 |Y_ij| 的相对最强关系识别 0-based 端口对。"""
    n = y_abs.shape[0]
    if n < 2:
        return []

    score = y_abs.copy()
    np.fill_diagonal(score, -np.inf)
    best = np.argmax(score, axis=1)
    best_strength = score[np.arange(n), best]

    pairs = set()
    used = set()
    for i, j in enumerate(best):
        j = int(j)
        if i in used or j in used or not np.isfinite(best_strength[i]) or best_strength[i] <= 0:
            continue
        if int(best[j]) == i and best_strength[j] > 0:
            lo, hi = sorted((i, j))
            pairs.add((lo, hi))
            used.add(i)
            used.add(j)
    return sorted(pairs)


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
) -> TopologyReport:
    """推断 1 驱 1 端口对。

    `band_ghz`、`y_threshold_siemens`、`s_threshold_db`、`delay_tolerance_ns`
    保留为兼容参数，本版不参与判别。
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

    pairs = _mutual_strongest_pairs(y_abs)
    paired_ports = set()
    channels: List[ChannelInfo] = []
    for lo, hi in pairs:
        p_lo, p_hi = lo + 1, hi + 1
        paired_ports.update((p_lo, p_hi))
        channels.append(ChannelInfo(
            ports=[p_lo, p_hi],
            tx=p_lo,
            rxs=[p_hi],
            s_value=complex(s_mat[lo, hi]),
            z_value=complex(z_mat[lo, hi]) if z_mat is not None else None,
            topology="p2p",
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
    """把 TopologyReport 渲染成可读文本，供主窗口控制台输出。"""
    lines: List[str] = []
    head = f"=== 拓扑识别"
    if file_label:
        head += f"：{file_label}"
    head += " ==="
    lines.append(head)
    lines.append(
        f"端口数 = {report.n_ports}，"
        f"低频探测点 = {report.low_freq_ghz:.4f} GHz，"
        "判别方式 = 低频 |Y_ij| 互为最强"
    )
    if not report.channels:
        lines.append("未识别到任何耦合端口对。")
    for idx, ch in enumerate(report.channels, start=1):
        rx = ch.rxs[0] if ch.rxs else None
        if rx is not None:
            lines.append(
                f"联通端口对 {idx}: port {ch.tx} -> port {rx}  "
                f"(S{ch.tx},{rx}={_format_s_db(ch.s_value)}, "
                f"|Z{ch.tx},{rx}|={_format_abs(ch.z_value, ' Ω')})"
            )
    if report.isolated_ports:
        lines.append(
            "孤立端口（未与任何端口形成显著耦合）：" +
            ", ".join(str(p) for p in report.isolated_ports)
        )
    return "\n".join(lines)
