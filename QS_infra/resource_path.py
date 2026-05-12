"""PyInstaller 冻结环境下的资源路径解析。"""

import os
import sys


def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，兼容开发环境和 PyInstaller 打包环境。"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
