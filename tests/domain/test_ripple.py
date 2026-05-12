"""QS_domain/algorithms/ripple.py 的单元测试（不需要 QApplication）。"""

import numpy as np
import skrf as rf
import pytest
from QS_domain.algorithms.ripple import ripple_calc, _ieee_8023_fit


def _make_network(n_ports: int = 2, n_freqs: int = 100,
                  f_start: float = 1e9, f_stop: float = 10e9) -> rf.Network:
    """创建测试用的 skrf.Network（纯合成数据）。"""
    freq = rf.Frequency(f_start / 1e9, f_stop / 1e9, n_freqs, 'ghz')
    s = np.zeros((n_freqs, n_ports, n_ports), dtype=complex)
    for i in range(n_ports):
        s[:, i, i] = 0.1 * np.exp(1j * np.linspace(0, 2 * np.pi, n_freqs))
    s[:, 0, 1] = 0.9 * np.exp(-1j * np.linspace(0, 4 * np.pi, n_freqs))
    s[:, 1, 0] = s[:, 0, 1]
    ntwk = rf.Network(frequency=freq, s=s)
    ntwk.name = "test_network"
    return ntwk


class TestIeee8023Fit:
    def test_returns_correct_keys(self):
        freqG = np.linspace(1, 10, 50)
        data = -0.5 * np.sqrt(freqG * 1e9) * 1e-5
        result = _ieee_8023_fit(freqG, data)
        assert set(result.keys()) == {'fitted_curve', 'coeffs', 'formula'}

    def test_fitted_curve_shape(self):
        freqG = np.linspace(1, 10, 50)
        data = np.zeros(50)
        result = _ieee_8023_fit(freqG, data)
        assert result['fitted_curve'].shape == (50,)

    def test_formula_is_string(self):
        freqG = np.linspace(1, 10, 50)
        result = _ieee_8023_fit(freqG, np.zeros(50))
        assert isinstance(result['formula'], str)
        assert 'IL(f)' in result['formula']


class TestRippleCalc:
    def setup_method(self):
        self.ntwk = _make_network()

    def test_returns_required_keys(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "n次多项式", {'order': 3})
        required = {'label', 'freqG_range', 's_param_range', 'fitted_curve',
                    'residuals', 'max_ripple', 'max_ripple_freqG',
                    'max_ripple_index', 'formula'}
        assert required.issubset(result.keys())

    def test_label_format(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "n次多项式", {'order': 3})
        assert 'S1,2' in result['label']

    def test_freq_range_clipped(self):
        result = ripple_calc(self.ntwk, 1, 2, 3.0, 7.0,
                             "幅度 (dB)", "n次多项式", {'order': 3})
        assert result['freqG_range'].min() >= 3.0 - 0.1
        assert result['freqG_range'].max() <= 7.0 + 0.1

    def test_residuals_shape_matches(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "n次多项式", {'order': 3})
        assert result['residuals'].shape == result['s_param_range'].shape

    def test_max_ripple_is_float(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "n次多项式", {'order': 3})
        assert isinstance(result['max_ripple'], float)

    def test_ieee_method(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "IEEE_std_802.3-2022", {})
        assert result['formula'] is not None
        assert 'IL(f)' in result['formula']

    def test_savgol_method(self):
        result = ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                             "幅度 (dB)", "平滑函数",
                             {'window_length': 11, 'polyorder': 3})
        assert result['formula'] is None
        assert result['residuals'] is not None

    def test_unsupported_data_mode_raises(self):
        with pytest.raises(ValueError, match="暂不支持"):
            ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                        "未知模式", "n次多项式", {'order': 3})

    def test_unsupported_method_raises(self):
        with pytest.raises(ValueError, match="未知拟合方法"):
            ripple_calc(self.ntwk, 1, 2, 1.0, 10.0,
                        "幅度 (dB)", "未知方法", {})
