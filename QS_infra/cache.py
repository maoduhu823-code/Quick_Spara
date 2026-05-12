"""网络对象缓存，基于文件指纹（mtime + size）。"""

from __future__ import annotations

import os
import numpy as np
import skrf as rf


class NetworkCache:
    """
    管理 skrf.Network 对象和派生参数矩阵（S/Y/Z）的内存缓存。

    - 磁盘文件通过 mtime+size 指纹检测变化，自动失效。
    - 内存生成的 Network（注册时 fingerprint=None）不做磁盘检查。
    """

    _PARAM_ATTRS = {'S参数': 's', 'Y参数': 'y', 'Z参数': 'z'}

    def __init__(self):
        self._networks: dict[str, rf.Network] = {}
        self._fingerprints: dict[str, tuple | None] = {}
        self._params: dict[str, dict[str, np.ndarray]] = {
            'S参数': {}, 'Y参数': {}, 'Z参数': {}
        }
        self.debug: bool = False

    # ── 日志 ─────────────────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        if self.debug:
            print(msg)

    # ── 指纹 ─────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_fingerprint(file_name: str) -> tuple | None:
        """返回磁盘文件指纹；文件不存在或为内存对象时返回 None。"""
        if not isinstance(file_name, str) or not os.path.isfile(file_name):
            return None
        try:
            stat = os.stat(file_name)
            return (os.path.abspath(file_name), stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def _is_stale(self, key: str) -> bool:
        """检查磁盘文件是否已更新（仅对有指纹的条目有效）。"""
        if key not in self._networks:
            return False
        current_fp = self.compute_fingerprint(key)
        cached_fp = self._fingerprints.get(key)
        return (current_fp is not None and cached_fp is not None
                and current_fp != cached_fp)

    # ── 网络对象 CRUD ─────────────────────────────────────────────────────────

    def has_network(self, key: str) -> bool:
        return key in self._networks

    def get_raw_networks(self) -> dict[str, rf.Network]:
        """暴露内部字典引用，供需要直接访问 s_data 的旧代码使用。"""
        return self._networks

    def get_network(self, key: str) -> rf.Network | None:
        if self._is_stale(key):
            self._log(f"[cache] stale: {key}")
            self.invalidate(key, include_network=True)
        if key in self._networks:
            self._log(f"[cache] hit: {key}")
            return self._networks[key]
        return None

    def put_network(self, key: str, network: rf.Network, fingerprint: tuple | None = None) -> None:
        self._networks[key] = network
        self._fingerprints[key] = fingerprint
        self._log(f"[cache] put: {key}")

    def register_network(self, key: str, network: rf.Network) -> None:
        """注册内存生成的 Network（无指纹）。"""
        self.invalidate(key, include_network=True)
        self._networks[key] = network
        self._fingerprints[key] = None
        self._log(f"[cache] register: {key}")

    # ── 参数矩阵 ──────────────────────────────────────────────────────────────

    def get_param(self, key: str, param_type: str) -> np.ndarray | None:
        if param_type not in self._PARAM_ATTRS:
            raise ValueError(f"未知参数类型: {param_type}")
        cached = self._params[param_type].get(key)
        if cached is not None:
            self._log(f"[cache] {param_type} hit: {key}, shape={cached.shape}")
            return cached
        return None

    def put_param(self, key: str, param_type: str, matrix: np.ndarray) -> None:
        if param_type not in self._PARAM_ATTRS:
            raise ValueError(f"未知参数类型: {param_type}")
        self._params[param_type][key] = matrix
        self._log(f"[cache] {param_type} put: {key}, shape={matrix.shape}")

    # ── 失效 ─────────────────────────────────────────────────────────────────

    def invalidate(self, key: str, include_network: bool = False) -> None:
        """清理单文件缓存；include_network=True 时同时移除 Network 对象。"""
        for cache in self._params.values():
            cache.pop(key, None)
        if include_network:
            self._networks.pop(key, None)
            self._fingerprints.pop(key, None)
        self._log(f"[cache] invalidate: {key}, include_network={include_network}")

    def clear_all(self) -> None:
        self._networks.clear()
        self._fingerprints.clear()
        for cache in self._params.values():
            cache.clear()
        self._log("[cache] clear all")
