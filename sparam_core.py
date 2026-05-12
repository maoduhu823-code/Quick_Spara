"""
sparam_core — 向后兼容的 re-export shim。

所有算法实现已迁移到 QS_domain/ 层。
此文件保留原有导入路径，不破坏任何现有调用方。
"""

# === 阻抗工具 ===
from QS_domain.algorithms.impedance import (          # noqa: F401
    has_zero_impedance,
    replace_zero_impedance,
    enforce_nonzero_z0,
)

# === 差分转换 ===
from QS_domain.algorithms.se2diff import (            # noqa: F401
    SE2diff,
    SE2dq_dqs,
    SE2diff_port,
)

# === 纹波分析 ===
from QS_domain.algorithms.ripple import ripple_calc   # noqa: F401

# === 端口合并 ===
from QS_domain.algorithms.port_merge import merge_ports_multi  # noqa: F401

# === 时域分析 ===
from QS_domain.algorithms.time_domain import (        # noqa: F401
    td_default_params,
    td_compat_check,
    compute_time_domain,
)

# === 端口字符串解析（含 UI 错误提示的包装层）===

from PyQt6.QtWidgets import QMessageBox


def parse_port_input(input_str: str, type: str = 'port'):
    """
    解析端口/频率输入字符串。
    格式错误时弹出 QMessageBox 并返回 None（向后兼容旧调用方）。
    纯算法实现见 QS_domain.port_parser.parse_port_input。
    """
    from QS_domain.port_parser import parse_port_input as _pure
    try:
        return _pure(input_str, type)
    except ValueError as e:
        QMessageBox.warning(None, '输入错误',
                            f'输入格式错误！\n错误详情: {str(e)}\n'
                            '请输入以下格式之一:\n'
                            '1:5 或 1:2:5（可用中文或英文冒号）\n'
                            '[1,3,5] 或 [1 3 5] 或 1 3 5')
        return None
