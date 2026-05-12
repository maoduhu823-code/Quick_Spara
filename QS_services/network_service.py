"""
NetworkService — 管理 skrf.Network 对象集合的应用服务。

职责：文件加载、缓存协调、参数矩阵懒计算。
无 Qt 依赖：加载失败抛出 NetworkLoadError，由 UI 层捕获并展示。
"""

from __future__ import annotations

import numpy as np
import skrf as rf

from QS_infra.cache import NetworkCache
from QS_domain.algorithms.impedance import enforce_nonzero_z0


class NetworkLoadError(Exception):
    """网络加载或参数计算失败时抛出。"""


class NetworkService:
    """
    封装 Network 对象的生命周期管理。

    主窗口持有一个 NetworkService 实例；
    需要访问数据的对话框通过 parent.get_network() 等委托方法访问，
    保持与原有调用接口完全兼容。
    """

    def __init__(self, cache: NetworkCache = None):
        self._cache = cache or NetworkCache()

    # ── 调试开关（由 UI 层驱动） ──────────────────────────────────────────────

    @property
    def debug(self) -> bool:
        return self._cache.debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._cache.debug = value

    # ── 暴露 s_data 供旧代码直接传参（freq_analysis / time_domain 对话框）──────

    @property
    def s_data(self) -> dict[str, rf.Network]:
        return self._cache.get_raw_networks()

    # ── 核心接口 ──────────────────────────────────────────────────────────────

    def get_network(self, file_name: str) -> rf.Network:
        """从缓存获取或加载网络对象；磁盘文件变化时自动重载。"""
        network = self._cache.get_network(file_name)
        if network is None:
            network = rf.Network(file_name)
            enforce_nonzero_z0(network, file_name)
            fingerprint = NetworkCache.compute_fingerprint(file_name)
            self._cache.put_network(file_name, network, fingerprint)
        return network

    def register_network(self, file_name: str, network: rf.Network) -> None:
        """注册内存生成的 Network，并清理同名旧参数缓存。"""
        self._cache.register_network(file_name, network)

    def get_param_matrix(self, file_name: str, param_type: str) -> np.ndarray | None:
        """统一获取 S/Y/Z 矩阵，懒加载并缓存。返回 None 表示加载失败。"""
        network = self.get_network(file_name)

        cached = self._cache.get_param(file_name, param_type)
        if cached is not None:
            return cached

        attr_map = {'S参数': 's', 'Y参数': 'y', 'Z参数': 'z'}
        if param_type not in attr_map:
            raise ValueError(f"未知参数类型: {param_type}")

        try:
            matrix = getattr(network, attr_map[param_type])
            self._cache.put_param(file_name, param_type, matrix)
            return matrix
        except Exception as e:
            raise NetworkLoadError(
                f"无法读取 {file_name} 的 {param_type}:\n{str(e)}"
            ) from e

    def get_s(self, file_name: str) -> np.ndarray | None:
        return self.get_param_matrix(file_name, 'S参数')

    def get_y(self, file_name: str) -> np.ndarray | None:
        return self.get_param_matrix(file_name, 'Y参数')

    def get_z(self, file_name: str) -> np.ndarray | None:
        return self.get_param_matrix(file_name, 'Z参数')

    def invalidate_file_cache(self, file_name: str, include_network: bool = False) -> None:
        """清理单个文件的派生参数缓存；必要时同时移除 Network 对象。"""
        self._cache.invalidate(file_name, include_network=include_network)

    def clear_all_cache(self) -> None:
        self._cache.clear_all()
