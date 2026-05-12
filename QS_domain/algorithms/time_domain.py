"""时域变换算法（无 UI 依赖）。"""

from __future__ import annotations

import os
import numpy as np
import skrf as rf


def td_default_params(network: rf.Network) -> dict:
    """从 S 参数频率特性推算默认时域参数。"""
    f = network.f
    fmax = f[-1]
    df = (f[-1] - f[0]) / (len(f) - 1) if len(f) > 1 else f[-1]
    N_dc = max(0, round(f[0] / df))
    N_f_total = len(f) + N_dc
    n_natural = 2 * (N_f_total - 1)
    n_points = int(2 ** np.ceil(np.log2(max(n_natural, 4))))
    tr_ps = 0.35 / (fmax / 1e9) * 1000
    dt_nyq_ps = 1e12 / (2 * fmax)
    T_total_ps = 1e12 / df
    return {
        "tr_ps":      round(tr_ps, 2),
        "dt_ps":      round(dt_nyq_ps, 4),
        "n_points":   n_points,
        "fmax_GHz":   fmax / 1e9,
        "df_GHz":     df / 1e9,
        "T_total_ps": round(T_total_ps, 2),
        "dt_nyq_ps":  round(dt_nyq_ps, 4),
        "N_f_total":  N_f_total,
    }


def td_compat_check(network: rf.Network, tr_ps: float,
                    dt_ps: float, n_points: int) -> dict:
    """实时兼容性检查。不做计算，只做范围判断。"""
    f = network.f
    fmax = f[-1]
    df = (f[-1] - f[0]) / (len(f) - 1) if len(f) > 1 else f[-1]
    tr_min_ps = 0.35 / (fmax / 1e9) * 1000
    dt_nyq_ps = 1e12 / (2 * fmax)
    T_total_ps = 1e12 / df

    status = {"tr": "ok", "dt": "ok", "n": "ok", "messages": []}

    if tr_ps < tr_min_ps * 0.9:
        status["tr"] = "warn"
        status["messages"].append(
            f"上升沿 {tr_ps:.1f}ps < 数据最小值 {tr_min_ps:.1f}ps，需高频外推，可能产生伪峰")

    if dt_ps > dt_nyq_ps * 1.05:
        status["dt"] = "error"
        status["messages"].append(
            f"时间步长 {dt_ps:.2f}ps > Nyquist {dt_nyq_ps:.2f}ps，存在时域混叠风险")
    elif dt_ps < dt_nyq_ps * 0.5:
        status["dt"] = "warn"
        status["messages"].append(
            f"时间步长 {dt_ps:.2f}ps 很小（Nyquist={dt_nyq_ps:.2f}ps），通过补零实现，不增加实际信息")

    T_expected_ps = n_points * dt_ps
    if T_expected_ps > T_total_ps * 1.1:
        status["n"] = "warn"
        status["messages"].append(
            f"时间窗口 {T_expected_ps:.0f}ps > 频率分辨率限制 {T_total_ps:.0f}ps，需要对频率轴插值")

    return status


def _td_impulse_response(freq_full: np.ndarray, s_full: np.ndarray,
                          n_fft: int, tr_ps: float,
                          window_type: str = "gaussian") -> tuple[np.ndarray, np.ndarray]:
    """计算冲激响应（内部函数）。freq_full 必须从 f=0 开始，间距为 df。

    window_type : "gaussian" | "rect" | "hanning" | "hamming" | "blackman"
    """
    df_Hz = freq_full[1] if len(freq_full) > 1 else freq_full[-1]

    sigma_f = 0.35 / (tr_ps * 1e-12)
    x = np.pi * freq_full / sigma_f
    if window_type == "rect":
        W = (freq_full <= sigma_f).astype(float)
    elif window_type == "hanning":
        W = np.where(freq_full <= sigma_f, 0.5 * (1.0 + np.cos(x)), 0.0)
    elif window_type == "hamming":
        W = np.where(freq_full <= sigma_f, 0.54 + 0.46 * np.cos(x), 0.0)
    elif window_type == "blackman":
        W = np.where(freq_full <= sigma_f,
                     0.42 + 0.5 * np.cos(x) + 0.08 * np.cos(2.0 * x), 0.0)
    else:  # gaussian（默认）
        W = np.exp(-0.5 * (freq_full / sigma_f) ** 2)

    s_windowed = s_full * W
    n_freq_needed = n_fft // 2 + 1
    s_padded = np.zeros(n_freq_needed, dtype=complex)
    n_copy = min(len(s_windowed), n_freq_needed)
    s_padded[:n_copy] = s_windowed[:n_copy]

    h_t = np.fft.irfft(s_padded, n=n_fft)
    dt_s = 1.0 / (n_fft * df_Hz)
    time_s = np.arange(n_fft) * dt_s
    return time_s, h_t


def _td_step_response(h_t: np.ndarray) -> np.ndarray:
    return np.cumsum(h_t)


def _td_tdr_impedance(step_t: np.ndarray, z0: float) -> np.ndarray:
    gamma = np.clip(np.real(step_t), -0.9999, 0.9999)
    return z0 * (1.0 + gamma) / (1.0 - gamma)


def compute_time_domain(
        network: rf.Network,
        p1: int,
        p2: int,
        waveform: str = "TDR",
        tr_ps: float = None,
        dt_ps: float = None,
        n_points: int = None,
        z0: float = 50.0,
        pulse_width_ps: float = None,
        window_type: str = "gaussian",
        s_params: np.ndarray = None,
) -> dict:
    """
    计算时域波形。

    waveform    : "TDR" | "impulse" | "step" | "pulse"
    window_type : "gaussian" | "rect" | "hanning" | "hamming" | "blackman"

    返回 {"time_ps", "y_data", "label", "y_label", "compat_status"}
    """
    freq_orig = network.f
    if s_params is None:
        s_params = network.s
    s_orig = s_params[:, p1 - 1, p2 - 1]
    df_Hz = (freq_orig[-1] - freq_orig[0]) / (len(freq_orig) - 1)

    defaults = td_default_params(network)
    tr_ps = tr_ps if tr_ps is not None else defaults["tr_ps"]

    if n_points is None:
        if dt_ps is not None:
            T_total_ps = 1e12 / df_Hz
            n_raw = int(np.ceil(T_total_ps / dt_ps))
            n_points = int(2 ** np.ceil(np.log2(max(n_raw, 4))))
        else:
            n_points = defaults["n_points"]
    if dt_ps is None:
        dt_ps = defaults["dt_ps"]

    compat = td_compat_check(network, tr_ps, dt_ps, n_points)

    s_dc = 0.0 if (p1 == p2) else 1.0
    if freq_orig[0] > 0:
        N_dc = max(1, round(freq_orig[0] / df_Hz))
        dc_part = np.linspace(s_dc, np.real(s_orig[0]), N_dc) + 0j
        s_full = np.concatenate([dc_part, s_orig])
        freq_full = np.arange(len(s_full)) * df_Hz
    else:
        s_full = s_orig.copy()
        freq_full = freq_orig.copy()

    time_s, h_t = _td_impulse_response(freq_full, s_full, n_points, tr_ps, window_type)
    dt_s = time_s[1] - time_s[0] if len(time_s) > 1 else 1.0
    step_t = _td_step_response(h_t)

    if waveform == "TDR":
        y_data = _td_tdr_impedance(step_t, z0)
        y_label = "Impedance (Ω)"
    elif waveform == "step":
        y_data = step_t
        y_label = "Step Response"
    elif waveform == "impulse":
        y_data = h_t
        y_label = "h(t)"
    elif waveform == "pulse":
        pw_ps = pulse_width_ps if pulse_width_ps else dt_ps * 10
        n_shift = max(1, round(pw_ps * 1e-12 / dt_s))
        shifted = np.zeros_like(step_t)
        shifted[n_shift:] = step_t[:-n_shift]
        y_data = step_t - shifted
        y_label = "Pulse Response"
    else:
        y_data = step_t
        y_label = "Step Response"

    net_name = network.name or ""
    label = f"{os.path.basename(net_name)}_S{p1},{p2}_{waveform}"
    return {
        "time_ps":       time_s * 1e12,
        "y_data":        np.real(y_data),
        "label":         label,
        "y_label":       y_label,
        "compat_status": compat,
    }
