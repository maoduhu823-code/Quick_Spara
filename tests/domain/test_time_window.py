"""QS_domain/algorithms/time_domain.suggest_time_window 的单元测试。"""

import numpy as np
import skrf as rf
import pytest

from QS_domain.algorithms.time_domain import (
    suggest_time_window, compute_time_domain,
)


class TestSuggestTimeWindow:
    def test_empty_returns_zeros(self):
        lo, hi = suggest_time_window(np.array([]), dt_s=1e-12)
        assert lo == 0.0 and hi == 0.0

    def test_all_zero_returns_full_range(self):
        n = 100
        dt = 1e-12
        lo, hi = suggest_time_window(np.zeros(n), dt_s=dt)
        # 退化为整段时间
        assert lo == 0.0
        assert hi == pytest.approx(n * dt)

    def test_centered_impulse_window_around_peak(self):
        # 在 t = 500*dt 处放置高斯冲激
        n = 2000
        dt = 1e-12
        t_idx = np.arange(n)
        sigma = 20
        peak_idx = 500
        h = np.exp(-0.5 * ((t_idx - peak_idx) / sigma) ** 2)

        lo, hi = suggest_time_window(h, dt_s=dt, waveform="impulse")
        # 推荐窗口应包含主峰位置
        assert lo <= peak_idx * dt <= hi
        # 窗口宽度远小于总长（这正是我们想要的效果）
        assert (hi - lo) < 0.5 * n * dt

    def test_step_window_wider_than_impulse(self):
        n = 2000
        dt = 1e-12
        t_idx = np.arange(n)
        h = np.exp(-0.5 * ((t_idx - 800) / 30) ** 2)

        lo_i, hi_i = suggest_time_window(h, dt_s=dt, waveform="impulse")
        lo_s, hi_s = suggest_time_window(h, dt_s=dt, waveform="step")
        # step 的右侧 padding 倍数更大 → 推荐右端更靠后
        assert hi_s >= hi_i

    def test_left_padding_does_not_go_negative(self):
        # 冲激在 t=0 附近，左 pad 不应越界为负
        n = 1000
        dt = 1e-12
        h = np.zeros(n)
        h[0:5] = np.array([1.0, 0.8, 0.6, 0.4, 0.2])
        lo, hi = suggest_time_window(h, dt_s=dt, waveform="impulse")
        assert lo >= 0.0

    def test_right_bound_clamped_to_length(self):
        # 冲激在序列末尾附近，右 pad 不应越界
        n = 1000
        dt = 1e-12
        h = np.zeros(n)
        h[-5:] = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
        lo, hi = suggest_time_window(h, dt_s=dt, waveform="step")
        assert hi <= (n - 1) * dt + 1e-18  # 允许浮点误差

    def test_threshold_factor_widens_window(self):
        n = 2000
        dt = 1e-12
        t_idx = np.arange(n)
        h = np.exp(-0.5 * ((t_idx - 800) / 30) ** 2)

        lo_tight, hi_tight = suggest_time_window(h, dt_s=dt, threshold_factor=0.1)
        lo_loose, hi_loose = suggest_time_window(h, dt_s=dt, threshold_factor=0.001)
        # 阈值更低 → 视为"活动"的样本更多 → 窗口更宽
        assert (hi_loose - lo_loose) >= (hi_tight - lo_tight)


class TestComputeTimeDomainReturnsImpulse:
    """compute_time_domain 必须返回冲激响应供 suggest_time_window 使用。"""

    def setup_method(self):
        # 简单 2 端口理想直通：S21=1, 其余=0
        freq = rf.Frequency(0.1, 10.0, 100, 'ghz')
        s = np.zeros((100, 2, 2), dtype=complex)
        s[:, 1, 0] = 1.0
        s[:, 0, 1] = 1.0
        self.ntwk = rf.Network(frequency=freq, s=s, z0=50.0, name="thru")

    def test_result_contains_impulse_and_dt(self):
        result = compute_time_domain(self.ntwk, 1, 2, waveform="impulse")
        assert "impulse_h_t" in result
        assert "dt_s" in result
        assert isinstance(result["impulse_h_t"], np.ndarray)
        assert result["dt_s"] > 0

    def test_impulse_can_drive_suggest_window(self):
        result = compute_time_domain(self.ntwk, 1, 2, waveform="impulse")
        lo, hi = suggest_time_window(
            result["impulse_h_t"], result["dt_s"], waveform="impulse")
        # 应返回有意义的非空区间
        assert hi > lo
        # 区间应远小于完整时间范围（这就是我们想要的）
        full = result["impulse_h_t"].size * result["dt_s"]
        assert (hi - lo) < full

    @pytest.mark.parametrize("wf", ["impulse", "step", "TDR", "pulse"])
    def test_all_waveforms_return_impulse(self, wf):
        result = compute_time_domain(self.ntwk, 1, 2, waveform=wf)
        assert "impulse_h_t" in result
        assert result["impulse_h_t"].size > 0
