"""
绘图数据变换服务（无 Qt/matplotlib 依赖）。

将复数 S/Y/Z 矩阵切片转换为可直接绘图的实数 y_data，
与 UI 层和 matplotlib 状态完全解耦，便于单元测试。
"""

from __future__ import annotations

import numpy as np

from QS_domain.display_config import DEFAULT_SCALES  # noqa: F401 — re-exported for callers


def compute_param_data(
        param: np.ndarray,
        facet: str,
        freqG: np.ndarray,
) -> tuple[np.ndarray, str]:
    """
    将复数参数切片转换为 (y_data, y_label)。

    param  : 1-D 复数数组，长度 = 频点数
    facet  : 显示模式字符串（见 _FACET_OPTIONS）
    freqG  : 1-D 浮点频率数组（GHz），仅群延迟计算需要
    """
    if facet == '幅度(dB)':
        return 20 * np.log10(np.abs(param)), '幅度 (dB)'
    elif facet in ('幅度(abs)', '导纳(abs)'):
        return np.abs(param), '幅度 (abs)'
    elif facet == '阻抗(mΩ)':
        return 1000 * np.abs(param), '阻抗 (mΩ)'
    elif facet == '相位(度)':
        return np.angle(param) * 180 / np.pi, '相位 (度)'
    elif facet == '相位(rad)':
        return np.angle(param), '相位 (rad)'
    elif facet == 'unwrap相位(度)':
        return np.unwrap(np.angle(param)) * 180 / np.pi, 'unwrap 相位 (度)'
    elif facet == 'unwrap相位(rad)':
        return np.unwrap(np.angle(param)), 'unwrap 相位 (rad)'
    elif facet == '群延迟(fs)':
        phase = np.unwrap(np.angle(param))
        tau_g = -np.gradient(phase, freqG * 1e9) / (2 * np.pi)
        return tau_g * 1e15, '群延迟 (fs)'
    elif facet in ('实部', '实部(ESR)'):
        return np.real(param), '实部'
    elif facet == '虚部':
        return np.imag(param), '虚部'
    elif facet == '电容(pF)':
        with np.errstate(divide='ignore', invalid='ignore'):
            y = -1.0 / (2 * np.pi * freqG * 1e9 * np.imag(param)) * 1e12
        return y, '电容 (pF)'
    else:
        return np.abs(param), '幅度 (abs)'


def get_axis_labels(param_type: str, facet: str) -> tuple[str, str]:
    """返回 (x轴标签, y轴标签)。"""
    x_label = '频率 (GHz)'
    y_label = f'{param_type} {facet}'
    return x_label, y_label


def get_default_scales(param_type: str, facet: str) -> tuple[str, str]:
    """返回 (x_scale, y_scale)，默认均为 '线性'。"""
    return DEFAULT_SCALES.get((param_type, facet), ('线性', '线性'))
