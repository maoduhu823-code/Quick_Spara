"""纹波拟合算法（无 UI 依赖）。"""

from __future__ import annotations

import numpy as np
import skrf as rf
from scipy.signal import savgol_filter
from numpy.polynomial import Polynomial


def ripple_calc(
        network: rf.Network,
        p1: int,
        p2: int,
        start_freqG: float,
        stop_freqG: float,
        data_mode: str,
        method: str,
        fit_params: dict,
        s_params: np.ndarray = None,
) -> dict:
    """
    计算 S 参数纹波，返回结果字典，不绘图。

    fit_params 根据 method 不同包含:
        "n次多项式"          : {'order': int}
        "平滑函数"           : {'window_length': int, 'polyorder': int}
        "IEEE_std_802.3-2022": {}

    返回键: label, freqG_range, s_param_range, fitted_curve,
            residuals, max_ripple, max_ripple_freqG, max_ripple_index, formula
    """
    if s_params is None:
        s_params = network.s
    freqG = network.f / 1e9
    file_name = network.name
    s_param = s_params[:, p1 - 1, p2 - 1]
    label = f'{file_name.split("/")[-1]}_S{p1},{p2}'

    mask = (freqG >= start_freqG) & (freqG <= stop_freqG)
    freqG_range = freqG[mask]

    if data_mode == "幅度 (dB)":
        s_param_range = 20 * np.log10(np.abs(s_param[mask]))
    elif data_mode == "幅度 (abs)":
        s_param_range = np.abs(s_param[mask])
    elif data_mode == "unwrap相位 (度)":
        s_param_range = np.unwrap(np.angle(s_param[mask])) * 180 / np.pi
    elif data_mode == "unwrap相位 (rad)":
        s_param_range = np.unwrap(np.angle(s_param[mask]))
    else:
        raise ValueError(f"暂不支持该类型数据拟合: {data_mode}")

    s_param_fit = s_param_range - s_param_range[0]

    result_fit = None
    if method == "n次多项式":
        coeffs = Polynomial.fit(freqG_range, s_param_fit, fit_params['order']).convert().coef
        fitted_curve = np.polyval(coeffs[::-1], freqG_range) + s_param_range[0]
    elif method == "IEEE_std_802.3-2022":
        result_fit = _ieee_8023_fit(freqG_range, s_param_fit)
        fitted_curve = result_fit['fitted_curve']
    elif method == "平滑函数":
        fitted_curve = savgol_filter(
            s_param_range,
            window_length=fit_params['window_length'],
            polyorder=fit_params['polyorder']
        )
    else:
        raise ValueError(f"未知拟合方法: {method}")

    residuals = s_param_range - fitted_curve
    max_ripple = np.max(residuals)
    max_ripple_index = int(np.argmax(residuals))
    max_ripple_freqG = freqG_range[max_ripple_index]

    return {
        'label':            label,
        'freqG_range':      freqG_range,
        's_param_range':    s_param_range,
        'fitted_curve':     fitted_curve,
        'residuals':        residuals,
        'max_ripple':       float(max_ripple),
        'max_ripple_freqG': float(max_ripple_freqG),
        'max_ripple_index': max_ripple_index,
        'formula':          result_fit['formula'] if result_fit else None,
    }


def _ieee_8023_fit(freqG: np.ndarray, s_param_db: np.ndarray) -> dict:
    """IEEE 802.3-2022 标准拟合: IL(f) = a0 + a1*sqrt(f) + a2*f + a4*f^2"""
    freq = freqG * 1e9
    X = np.column_stack([
        np.ones_like(freq),
        np.sqrt(freq),
        freq,
        freq ** 2
    ])
    coeffs, _, _, _ = np.linalg.lstsq(X, s_param_db, rcond=None)
    fitted = (coeffs[0] +
              coeffs[1] * np.sqrt(freq) +
              coeffs[2] * freq +
              coeffs[3] * freq ** 2)
    return {
        'fitted_curve': fitted,
        'coeffs': {'a0': coeffs[0], 'a1': coeffs[1], 'a2': coeffs[2], 'a4': coeffs[3]},
        'formula': "IL(f) = {a0:.3f} + {a1:.3g}*√f + {a2:.3g}*f + {a4:.3g}*f^2".format(
            a0=coeffs[0], a1=coeffs[1], a2=coeffs[2], a4=coeffs[3])
    }
