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
                  | "tukey" | "kaiser"
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
    elif window_type == "tukey":
        # 单边 Tukey：[0, (1-α)·σ_f] 平坦=1，过渡区余弦衰减到 0
        alpha = 0.5
        f_norm = freq_full / sigma_f
        W = np.zeros_like(freq_full, dtype=float)
        flat = f_norm <= (1.0 - alpha)
        taper = (f_norm > (1.0 - alpha)) & (f_norm <= 1.0)
        W[flat] = 1.0
        W[taper] = 0.5 * (1.0 + np.cos(
            np.pi * (f_norm[taper] - (1.0 - alpha)) / alpha))
    elif window_type == "kaiser":
        # 单边 Kaiser：W(f) = I0(β·√(1-(f/σ_f)²)) / I0(β)，f ≤ σ_f
        beta = 6.0
        f_norm = np.clip(freq_full / sigma_f, 0.0, 1.0)
        arg = beta * np.sqrt(np.clip(1.0 - f_norm ** 2, 0.0, None))
        W = np.where(freq_full <= sigma_f, np.i0(arg) / np.i0(beta), 0.0)
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


def suggest_time_window(
        h_t: np.ndarray,
        dt_s: float,
        waveform: str = "impulse",
        threshold_factor: float = 0.01,
        left_pad_frac: float = 0.1,
        right_pad_factor_by_wf: dict | None = None,
) -> tuple[float, float]:
    """根据冲激响应包络推荐显示时间窗口（秒）。

    思路：
      1. 取 |h(t)| 作包络；
      2. 找到 envelope > threshold_factor·peak 的首末点，作为冲激"活动区间"；
      3. 左侧 pad 出区间宽度的 left_pad_frac，提供前导上下文；
      4. 右侧 pad 出 right_pad_factor_by_wf[waveform] 倍区间宽度：
         - impulse / pulse 较小（看冲激本体即可）；
         - step / TDR 较大（要看趋于稳态的尾段）。

    Parameters
    ----------
    h_t : ndarray
        冲激响应序列（任意 waveform 都先经过 compute_time_domain 内部得到 h(t)）。
    dt_s : float
        时间步长（秒）。
    waveform : str
        "impulse" | "pulse" | "step" | "TDR"
    threshold_factor : float
        相对峰值的截断比例，默认 1%。
    left_pad_frac : float
        左侧 padding 比例。
    right_pad_factor_by_wf : dict | None
        各波形对应的右侧 padding 倍数。None 时使用内置默认。

    Returns
    -------
    (t_lo_s, t_hi_s) : tuple[float, float]
        建议 xlim，秒为单位。h_t 为空或全零时退化为 (0, len*dt)。
    """
    if right_pad_factor_by_wf is None:
        right_pad_factor_by_wf = {
            "impulse": 0.3,
            "pulse":   0.5,
            "step":    1.0,
            "TDR":     1.0,
        }

    env = np.abs(np.asarray(h_t))
    n = env.size
    if n == 0:
        return 0.0, 0.0
    peak = float(env.max())
    if peak <= 0.0:
        return 0.0, n * dt_s

    thresh = peak * threshold_factor
    above = np.where(env > thresh)[0]
    if above.size == 0:
        return 0.0, n * dt_s
    first_idx = int(above[0])
    last_idx = int(above[-1])

    width = max(1, last_idx - first_idx)
    pad_left = int(left_pad_frac * width)
    pad_right = int(right_pad_factor_by_wf.get(waveform, 0.5) * width)

    lo = max(0, first_idx - pad_left)
    hi = min(n - 1, last_idx + pad_right)
    return lo * dt_s, hi * dt_s


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
                  | "tukey" | "kaiser"

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

    # DC 外推：用前 K 点二次多项式拟合外推 Re(S(0))，强制 Im(S(0))=0
    # （因果实信号要求 S(0) ∈ ℝ；保留虚部连续过渡可抑制末端振铃和 t=0 偏移）
    if freq_orig[0] > 0:
        N_dc = max(1, round(freq_orig[0] / df_Hz))
        K = min(5, len(s_orig))
        deg = min(2, K - 1) if K >= 2 else 0
        re_coef = np.polyfit(freq_orig[:K], np.real(s_orig[:K]), deg)
        re_dc_val = float(np.clip(np.polyval(re_coef, 0.0), -1.0, 1.0))

        f_grid = np.arange(N_dc) * df_Hz
        if N_dc == 1:
            dc_re = np.array([re_dc_val])
            dc_im = np.array([0.0])
        else:
            t = f_grid / freq_orig[0]                       # 0 → ~1
            re_start = float(np.real(s_orig[0]))
            im_start = float(np.imag(s_orig[0]))
            dc_re = (1.0 - t) * re_dc_val + t * re_start    # 实部线性混合
            dc_im = t * im_start                            # 虚部从 0 平滑过渡

        dc_part = dc_re + 1j * dc_im
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
        # 冲激响应（实部），用于 suggest_time_window 推荐显示范围
        "impulse_h_t":   np.real(h_t),
        "dt_s":          float(dt_s),
    }
