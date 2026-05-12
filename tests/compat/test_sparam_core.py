"""
兼容层测试：验证 sparam_core.py 的旧导入路径仍然有效。

sparam_core 是向后兼容的 re-export shim，所有算法实现已迁移到 QS_domain。
"""

import numpy as np
import pytest


class TestSparamCoreReexports:
    """确认所有关键符号仍可从 sparam_core 导入。"""

    def test_import_has_zero_impedance(self):
        from sparam_core import has_zero_impedance
        assert callable(has_zero_impedance)

    def test_import_replace_zero_impedance(self):
        from sparam_core import replace_zero_impedance
        assert callable(replace_zero_impedance)

    def test_import_enforce_nonzero_z0(self):
        from sparam_core import enforce_nonzero_z0
        assert callable(enforce_nonzero_z0)

    def test_import_se2diff(self):
        from sparam_core import SE2diff, SE2dq_dqs, SE2diff_port
        assert callable(SE2diff)

    def test_import_ripple_calc(self):
        from sparam_core import ripple_calc
        assert callable(ripple_calc)

    def test_import_merge_ports_multi(self):
        from sparam_core import merge_ports_multi
        assert callable(merge_ports_multi)

    def test_import_compute_time_domain(self):
        from sparam_core import compute_time_domain
        assert callable(compute_time_domain)

    def test_import_parse_port_input(self):
        from sparam_core import parse_port_input
        assert callable(parse_port_input)


class TestImpedancePureFunctions:
    def test_has_zero_impedance_false_for_normal_network(self):
        import skrf as rf
        from sparam_core import has_zero_impedance
        freq = rf.Frequency(1, 10, 10, 'GHz')
        s = np.zeros((10, 2, 2), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=50)
        assert has_zero_impedance(ntwk) is False

    def test_has_zero_impedance_true_for_zero_z0(self):
        import skrf as rf
        from sparam_core import has_zero_impedance
        freq = rf.Frequency(1, 10, 10, 'GHz')
        s = np.zeros((10, 2, 2), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=0)
        assert has_zero_impedance(ntwk) is True

    def test_replace_zero_impedance(self):
        import skrf as rf
        from sparam_core import replace_zero_impedance
        freq = rf.Frequency(1, 10, 10, 'GHz')
        s = np.zeros((10, 2, 2), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=0)
        replace_zero_impedance(ntwk, 75.0)
        assert np.all(ntwk.z0 == 75.0)

    def test_replace_zero_impedance_rejects_nonpositive(self):
        import skrf as rf
        from sparam_core import replace_zero_impedance
        freq = rf.Frequency(1, 10, 10, 'GHz')
        s = np.zeros((10, 2, 2), dtype=complex)
        ntwk = rf.Network(frequency=freq, s=s, z0=50)
        with pytest.raises(ValueError):
            replace_zero_impedance(ntwk, 0.0)
