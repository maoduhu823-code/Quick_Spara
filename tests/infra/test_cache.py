"""NetworkCache 单元测试。"""

import numpy as np
import pytest
import skrf as rf

from QS_infra.cache import NetworkCache


def _make_network(nports: int = 2, nfreqs: int = 10) -> rf.Network:
    freq = rf.Frequency(1, 10, nfreqs, 'GHz')
    s = np.zeros((nfreqs, nports, nports), dtype=complex)
    return rf.Network(frequency=freq, s=s, z0=50)


class TestNetworkCache:
    def setup_method(self):
        self.cache = NetworkCache()

    def test_put_and_get_network(self):
        ntwk = _make_network()
        self.cache.put_network("a", ntwk)
        assert self.cache.get_network("a") is ntwk

    def test_get_missing_returns_none(self):
        assert self.cache.get_network("nonexistent") is None

    def test_register_network_no_fingerprint(self):
        ntwk = _make_network()
        self.cache.register_network("mem_net", ntwk)
        assert self.cache.get_network("mem_net") is ntwk

    def test_put_and_get_param(self):
        ntwk = _make_network()
        self.cache.put_network("a", ntwk)
        matrix = np.ones((10, 2, 2))
        self.cache.put_param("a", "S参数", matrix)
        result = self.cache.get_param("a", "S参数")
        np.testing.assert_array_equal(result, matrix)

    def test_invalidate_clears_params_not_network(self):
        ntwk = _make_network()
        self.cache.put_network("a", ntwk)
        matrix = np.ones((10, 2, 2))
        self.cache.put_param("a", "S参数", matrix)
        self.cache.invalidate("a", include_network=False)
        assert self.cache.get_param("a", "S参数") is None
        assert self.cache.get_network("a") is ntwk

    def test_invalidate_with_network_removes_all(self):
        ntwk = _make_network()
        self.cache.put_network("a", ntwk)
        matrix = np.ones((10, 2, 2))
        self.cache.put_param("a", "S参数", matrix)
        self.cache.invalidate("a", include_network=True)
        assert self.cache.get_param("a", "S参数") is None
        assert self.cache.get_network("a") is None

    def test_unknown_param_type_raises(self):
        with pytest.raises(ValueError, match="未知参数类型"):
            self.cache.get_param("a", "T参数")

    def test_fingerprint_nonexistent_file_returns_none(self):
        fp = NetworkCache.compute_fingerprint("/nonexistent/path/file.s2p")
        assert fp is None

    def test_clear_all(self):
        ntwk = _make_network()
        self.cache.put_network("a", ntwk)
        self.cache.put_param("a", "S参数", np.ones((10, 2, 2)))
        self.cache.clear_all()
        assert self.cache.get_network("a") is None
        assert self.cache.get_param("a", "S参数") is None
