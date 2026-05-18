"""QS_domain/algorithms/topology_detect.py 的单元测试。"""

import numpy as np
import skrf as rf
import pytest

from QS_domain.algorithms.topology_detect import (
    detect_topology, format_report, ChannelInfo, TopologyReport
)


def _freq(n_pts=201, f_start_ghz=0.05, f_stop_ghz=10.0) -> rf.Frequency:
    return rf.Frequency(f_start_ghz, f_stop_ghz, n_pts, 'ghz')


def _tline_s(freq: rf.Frequency, length_m: float, eps_r: float = 4.0,
             alpha_np_per_m: float = 0.1, z0: float = 50.0) -> np.ndarray:
    """单根理想 / 微损 50Ω 传输线（2 端口）的 S 参数序列 (Nf,2,2)。"""
    c = 3e8
    beta = 2 * np.pi * freq.f * np.sqrt(eps_r) / c
    gamma = alpha_np_per_m + 1j * beta
    s21 = np.exp(-gamma * length_m)
    s = np.zeros((len(freq.f), 2, 2), dtype=complex)
    s[:, 0, 0] = 0.0
    s[:, 1, 1] = 0.0
    s[:, 0, 1] = s21
    s[:, 1, 0] = s21
    return s


def _block_diag_2x2(blocks: list) -> np.ndarray:
    """把若干个 (Nf,2,2) S 参数块沿对角组合成 (Nf, 2K, 2K)。块间互不耦合。"""
    nf = blocks[0].shape[0]
    k = len(blocks)
    out = np.zeros((nf, 2 * k, 2 * k), dtype=complex)
    for idx, b in enumerate(blocks):
        out[:, 2 * idx:2 * idx + 2, 2 * idx:2 * idx + 2] = b
    return out


# -------------------------------------------------------------------
# 1 驱 1 — 两条独立点对点链路（4 端口）
# -------------------------------------------------------------------

class TestPointToPoint:
    def setup_method(self):
        freq = _freq()
        # 端口顺序：1=TX_a, 2=RX_a, 3=TX_b, 4=RX_b
        block_a = _tline_s(freq, length_m=0.05)
        block_b = _tline_s(freq, length_m=0.10)
        s = _block_diag_2x2([block_a, block_b])
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="p2p_4port")

    def test_two_channels_detected(self):
        rep = detect_topology(self.ntwk)
        assert isinstance(rep, TopologyReport)
        assert len(rep.channels) == 2
        for ch in rep.channels:
            assert ch.topology == "p2p"
            assert len(ch.ports) == 2

    def test_pairings_are_correct(self):
        rep = detect_topology(self.ntwk)
        pairs = sorted([tuple(sorted(ch.ports)) for ch in rep.channels])
        assert pairs == [(1, 2), (3, 4)]

    def test_no_isolated_ports(self):
        rep = detect_topology(self.ntwk)
        assert rep.isolated_ports == []


# -------------------------------------------------------------------
# 一驱多 — 用合成 S 矩阵模拟单 TX 扇出到 3 个 RX
# -------------------------------------------------------------------

class TestOneToMany:
    """
    构造一个 4 端口 S 矩阵：
      port 1 = TX
      port 2,3,4 = RXs，分别离 TX 0.05 / 0.10 / 0.15 m
      RX 之间 |S| 较低（star 拓扑）
    """
    def setup_method(self):
        freq = _freq()
        c = 3e8
        eps_r = 4.0
        nf = len(freq.f)
        lens = [0.05, 0.10, 0.15]
        s = np.zeros((nf, 4, 4), dtype=complex)
        for k, L in enumerate(lens):
            beta = 2 * np.pi * freq.f * np.sqrt(eps_r) / c
            gamma = 0.05 + 1j * beta
            t = np.exp(-gamma * L) / np.sqrt(len(lens))  # 1/sqrt(N) 扇出
            s[:, k + 1, 0] = t
            s[:, 0, k + 1] = t
        # RX 之间留弱耦合（远低于 -25 dB）
        for i in range(1, 4):
            for j in range(1, 4):
                if i != j:
                    s[:, i, j] = 0.01
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="one_to_many")

    def test_single_channel(self):
        rep = detect_topology(self.ntwk)
        assert len(rep.channels) == 1

    def test_hub_is_port_1(self):
        rep = detect_topology(self.ntwk)
        ch = rep.channels[0]
        assert ch.tx == 1
        assert sorted(ch.rxs) == [2, 3, 4]

    def test_rx_sorted_by_delay(self):
        rep = detect_topology(self.ntwk)
        ch = rep.channels[0]
        # 0.05m / 0.10m / 0.15m 对应递增的群延迟
        assert ch.rxs == [2, 3, 4]
        assert ch.delays_ns == sorted(ch.delays_ns)

    def test_topology_is_branching(self):
        rep = detect_topology(self.ntwk)
        # 不强制 star vs multi-drop（取决于 RX-RX 路径），只要求不是 unknown / p2p
        assert rep.channels[0].topology in {"star", "multi-drop"}


# -------------------------------------------------------------------
# 孤立端口
# -------------------------------------------------------------------

class TestIsolatedPort:
    def setup_method(self):
        freq = _freq()
        block = _tline_s(freq, length_m=0.05)
        nf = len(freq.f)
        s = np.zeros((nf, 3, 3), dtype=complex)
        s[:, :2, :2] = block
        # port 3 与外界全部断开：S31, S32, S13, S23 = 0；S33 = 0（匹配）
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="with_isolated")

    def test_one_channel_and_one_isolated(self):
        rep = detect_topology(self.ntwk)
        assert len(rep.channels) == 1
        assert tuple(sorted(rep.channels[0].ports)) == (1, 2)
        assert rep.isolated_ports == [3]


# -------------------------------------------------------------------
# 边界 / 输入校验
# -------------------------------------------------------------------

class TestEdgeCases:
    def test_single_port_returns_isolated(self):
        freq = _freq(n_pts=21)
        s = np.zeros((len(freq.f), 1, 1), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=50.0)
        rep = detect_topology(ntwk)
        assert rep.channels == []
        assert rep.isolated_ports == [1]

    def test_format_report_runs(self):
        freq = _freq()
        block = _tline_s(freq, length_m=0.05)
        ntwk = rf.Network(frequency=freq, s=block, z0=50.0, name="t")
        rep = detect_topology(ntwk)
        text = format_report(rep, file_label="t.s2p")
        assert "拓扑识别" in text
        assert "t.s2p" in text
        # 至少应该出现 channel 行
        assert "Channel" in text or "未识别" in text

    def test_custom_band_clipped(self):
        freq = _freq()
        block = _tline_s(freq, length_m=0.05)
        ntwk = rf.Network(frequency=freq, s=block, z0=50.0)
        # 故意给越界的频段
        rep = detect_topology(ntwk, band_ghz=(50.0, 100.0))
        # 应该 fallback 到全频段或被裁剪，不应抛异常
        assert rep.n_ports == 2

    def test_loose_y_threshold_still_finds_pair(self):
        freq = _freq()
        block = _tline_s(freq, length_m=0.05)
        ntwk = rf.Network(frequency=freq, s=block, z0=50.0)
        rep = detect_topology(ntwk, y_threshold_siemens=1e-2)
        # 即使 Y 阈值放宽，S 阈值兜底仍应识别出 1↔2
        assert len(rep.channels) == 1
