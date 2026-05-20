"""QS_domain/algorithms/topology_detect.py 的单元测试。"""

import numpy as np
import skrf as rf
import pytest

from QS_domain.algorithms.topology_detect import detect_topology, format_report, TopologyReport


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

    def test_pair_report_contains_low_frequency_s_and_z_values(self):
        rep = detect_topology(self.ntwk)
        first = sorted(rep.channels, key=lambda ch: ch.ports)[0]
        # Z 仍写入数据结构，供后续 PI 场景使用；文本侧目前只显示 S。
        assert first.s_value is not None
        assert first.z_value is not None
        text = format_report(rep)
        assert "S1,2=" in text
        assert "|Z" not in text

    def test_no_isolated_ports(self):
        rep = detect_topology(self.ntwk)
        assert rep.isolated_ports == []


# -------------------------------------------------------------------
# 1 驱多 — 星型 4 端口（port 1 为 hub，2/3/4 为叶子）
# -------------------------------------------------------------------

def _star_s_from_y(n_branches: int, y_branch: float = 0.02, y_self: float = 0.025,
                   z0: float = 50.0) -> np.ndarray:
    """构造 (n_branches+1) 端口星型网络的 S 矩阵（单频点，频率无关）。

    Y 矩阵：hub 与每个 leaf 之间的互导纳 -y_branch；leaf 间互导纳为 0；
    leaf 对地 y_self；hub 对地 y_self。然后 S = (I - Z0 Y)(I + Z0 Y)^{-1}。
    """
    n = n_branches + 1
    Y = np.zeros((n, n), dtype=complex)
    for k in range(1, n):
        Y[0, k] = -y_branch
        Y[k, 0] = -y_branch
        Y[k, k] = y_branch + y_self
    Y[0, 0] = n_branches * y_branch + y_self
    Yn = z0 * Y
    eye = np.eye(n, dtype=complex)
    return (eye - Yn) @ np.linalg.inv(eye + Yn)


class TestMultiDrop:
    def setup_method(self):
        freq = _freq()
        nf = len(freq.f)
        n = 4
        S0 = _star_s_from_y(n_branches=n - 1)
        s = np.broadcast_to(S0, (nf, n, n)).copy()
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="star_4port")

    def test_single_multidrop_channel(self):
        rep = detect_topology(self.ntwk)
        assert len(rep.channels) == 1
        ch = rep.channels[0]
        assert ch.topology == "multi-drop"
        assert ch.tx == 1
        assert sorted(ch.rxs) == [2, 3, 4]
        assert rep.isolated_ports == []

    def test_multidrop_report_lists_all_rx_paths(self):
        rep = detect_topology(self.ntwk)
        text = format_report(rep, file_label="star.s4p")
        assert "联通簇" in text
        assert "4 端口" in text
        assert "port 1*" in text       # 中心节点带 * 标记
        assert "port 2" in text and "port 3" in text and "port 4" in text
        assert "S1,2=" in text
        assert "S1,3=" in text
        assert "S1,4=" in text

    def test_multidrop_rx_s_values_populated(self):
        rep = detect_topology(self.ntwk)
        ch = rep.channels[0]
        assert len(ch.rx_s_values) == 3
        assert len(ch.rx_z_values) == 3
        assert ch.s_value == ch.rx_s_values[0]


class TestMultiDropMixedWithP2P:
    """6 端口：port 1 驱 {2,3}（星型），port 4-5 是独立 trace，port 6 孤立。"""

    def setup_method(self):
        freq = _freq()
        nf = len(freq.f)
        # 3 端口星型（hub=0, leaves=1,2）
        star3 = _star_s_from_y(n_branches=2)
        # 2 端口 trace
        line2 = _tline_s(freq, length_m=0.05)
        # 把 star3（频率无关）扩成 (nf,3,3)
        star3_f = np.broadcast_to(star3, (nf, 3, 3)).copy()
        # 1 端口孤立段：S = 0（匹配吸收）
        iso = np.zeros((nf, 1, 1), dtype=complex)
        n = 6
        s = np.zeros((nf, n, n), dtype=complex)
        s[:, 0:3, 0:3] = star3_f
        s[:, 3:5, 3:5] = line2
        s[:, 5:6, 5:6] = iso
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="mixed_6port")

    def test_mixed_topology(self):
        rep = detect_topology(self.ntwk)
        by_topo = {ch.topology: ch for ch in rep.channels}
        assert "multi-drop" in by_topo
        assert "p2p" in by_topo
        multi = by_topo["multi-drop"]
        p2p = by_topo["p2p"]
        assert multi.tx == 1
        assert sorted(multi.rxs) == [2, 3]
        assert tuple(sorted(p2p.ports)) == (4, 5)
        assert rep.isolated_ports == [6]


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
        assert "联通端口对" in text or "未识别" in text

    def test_legacy_threshold_arguments_do_not_block_pairing(self):
        freq = _freq()
        block = _tline_s(freq, length_m=0.05)
        ntwk = rf.Network(frequency=freq, s=block, z0=50.0)
        rep = detect_topology(
            ntwk,
            band_ghz=(50.0, 100.0),
            y_threshold_siemens=1e9,
            s_threshold_db=0.0,
            delay_tolerance_ns=0.0,
        )
        assert len(rep.channels) == 1

    def test_zero_coupling_ports_are_isolated(self):
        freq = _freq(n_pts=21)
        s = np.zeros((len(freq.f), 2, 2), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=50.0)
        rep = detect_topology(ntwk)
        assert rep.channels == []
        assert rep.isolated_ports == [1, 2]
