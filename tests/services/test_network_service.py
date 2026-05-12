"""NetworkService 单元测试 — 不依赖 Qt。"""

import numpy as np
import pytest
import skrf as rf

from QS_services.network_service import NetworkService, NetworkLoadError


def _make_network(nports: int = 2, nfreqs: int = 10) -> rf.Network:
    freq = rf.Frequency(1, 10, nfreqs, 'GHz')
    s = np.zeros((nfreqs, nports, nports), dtype=complex)
    for i in range(nfreqs):
        s[i] = np.eye(nports) * 0.5
    return rf.Network(frequency=freq, s=s, z0=50)


class TestNetworkServiceRegister:
    def setup_method(self):
        self.svc = NetworkService()

    def test_register_and_retrieve(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        retrieved = self.svc.get_network("test_net")
        assert retrieved is ntwk

    def test_register_replaces_existing(self):
        ntwk1 = _make_network()
        ntwk2 = _make_network(nports=4)
        self.svc.register_network("test_net", ntwk1)
        self.svc.register_network("test_net", ntwk2)
        assert self.svc.get_network("test_net").nports == 4

    def test_get_s_param_matrix(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        s = self.svc.get_s("test_net")
        assert s is not None
        assert s.shape == (10, 2, 2)

    def test_get_y_param_matrix(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        y = self.svc.get_y("test_net")
        assert y is not None
        assert y.shape == (10, 2, 2)

    def test_get_z_param_matrix(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        z = self.svc.get_z("test_net")
        assert z is not None
        assert z.shape == (10, 2, 2)

    def test_unknown_param_type_raises(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        with pytest.raises(ValueError, match="未知参数类型"):
            self.svc.get_param_matrix("test_net", "T参数")

    def test_invalidate_clears_param_cache(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        _ = self.svc.get_s("test_net")
        self.svc.invalidate_file_cache("test_net")
        # After invalidation, network still accessible, params recomputed
        s2 = self.svc.get_s("test_net")
        assert s2 is not None

    def test_clear_all_cache(self):
        ntwk = _make_network()
        self.svc.register_network("test_net", ntwk)
        self.svc.clear_all_cache()
        # After clearing all, network is gone
        with pytest.raises(Exception):
            self.svc.get_network("test_net")


class TestNetworkLoadError:
    def test_network_load_error_is_exception(self):
        err = NetworkLoadError("test error")
        assert isinstance(err, Exception)
        assert "test error" in str(err)
