"""QS_services/plotting_service.py 的单元测试（不需要 QApplication / matplotlib）。"""

import numpy as np
import pytest
from QS_services.plotting_service import compute_param_data, get_default_scales


def _make_param(n: int = 50) -> tuple[np.ndarray, np.ndarray]:
    freqG = np.linspace(1, 10, n)
    param = (0.9 * np.exp(-1j * np.linspace(0, 4 * np.pi, n)) +
             0.01 * np.random.randn(n))
    return param, freqG


class TestComputeParamData:
    def setup_method(self):
        self.param, self.freqG = _make_param()

    def _run(self, facet):
        y, lbl = compute_param_data(self.param, facet, self.freqG)
        assert isinstance(y, np.ndarray), f"{facet} → not ndarray"
        assert y.shape == self.param.shape, f"{facet} → shape mismatch"
        assert isinstance(lbl, str), f"{facet} → label not str"
        return y, lbl

    def test_mag_db(self):
        y, _ = self._run('幅度(dB)')
        expected = 20 * np.log10(np.abs(self.param))
        np.testing.assert_allclose(y, expected)

    def test_mag_abs(self):
        y, _ = self._run('幅度(abs)')
        np.testing.assert_allclose(y, np.abs(self.param))

    def test_admittance(self):
        y, _ = self._run('导纳(abs)')
        np.testing.assert_allclose(y, np.abs(self.param))

    def test_impedance_m(self):
        y, _ = self._run('阻抗(mΩ)')
        np.testing.assert_allclose(y, 1000 * np.abs(self.param))

    def test_phase_deg(self):
        y, _ = self._run('相位(度)')
        expected = np.angle(self.param) * 180 / np.pi
        np.testing.assert_allclose(y, expected)

    def test_phase_rad(self):
        y, _ = self._run('相位(rad)')
        np.testing.assert_allclose(y, np.angle(self.param))

    def test_unwrap_deg(self):
        self._run('unwrap相位(度)')

    def test_unwrap_rad(self):
        self._run('unwrap相位(rad)')

    def test_group_delay(self):
        self._run('群延迟(fs)')

    def test_real(self):
        y, _ = self._run('实部')
        np.testing.assert_allclose(y, np.real(self.param))

    def test_esr(self):
        y, _ = self._run('实部(ESR)')
        np.testing.assert_allclose(y, np.real(self.param))

    def test_imag(self):
        y, _ = self._run('虚部')
        np.testing.assert_allclose(y, np.imag(self.param))

    def test_capacitance(self):
        self._run('电容(pF)')

    def test_unknown_facet_fallback(self):
        y, lbl = compute_param_data(self.param, '未知切面', self.freqG)
        np.testing.assert_allclose(y, np.abs(self.param))


class TestGetDefaultScales:
    def test_z_impedance_log(self):
        assert get_default_scales('Z参数', '阻抗(mΩ)') == ('对数', '对数')

    def test_y_admittance_log(self):
        assert get_default_scales('Y参数', '导纳(abs)') == ('对数', '对数')

    def test_z_esr_semilog(self):
        assert get_default_scales('Z参数', '实部(ESR)') == ('对数', '线性')

    def test_default_linear(self):
        assert get_default_scales('S参数', '幅度(dB)') == ('线性', '线性')
