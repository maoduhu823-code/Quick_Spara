"""脉冲响应诊断脚本：对 --dev 预设文件按多种频域窗输出时域波形对比图。

测试输入：C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p, port1=1, port2=3
关注问题：脉冲响应 t=0 不为 0、末端震荡。

用法：
    python dev_scripts/diag_pulse.py
    python dev_scripts/diag_pulse.py --tag fix1   # 给输出文件加 tag 区分多次尝试
"""
from __future__ import annotations

import argparse
import os
import sys
import numpy as np
import skrf as rf
import matplotlib
matplotlib.use("Agg")  # 仅出图存盘，不开窗
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

plt.rcParams["font.sans-serif"] = ["SimHei"] if sys.platform == "win32" else ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False

from QS_domain.algorithms.time_domain import compute_time_domain, td_default_params

TEST_FILE = r"C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p"
P1, P2 = 1, 3
WINDOWS = ["gaussian", "rect", "hanning", "hamming", "blackman", "tukey", "kaiser"]
ZH = {
    "gaussian": "高斯", "rect": "矩形", "hanning": "汉宁", "hamming": "汉明",
    "blackman": "布莱克曼", "tukey": "Tukey", "kaiser": "Kaiser",
}


def _summary(t_ps, y, label=""):
    """统计 t=0 值、末段 RMS、峰值时间。"""
    n = len(y)
    end_tail = y[int(n * 0.85):]
    return (
        f"  {label:>10s}  y[0]={y[0]:+.4e}  "
        f"|y_tail|_rms={np.sqrt(np.mean(end_tail ** 2)):+.4e}  "
        f"max={y.max():+.4e}@t={t_ps[np.argmax(y)]:.1f}ps  "
        f"min={y.min():+.4e}@t={t_ps[np.argmin(y)]:.1f}ps"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="default", help="输出图片文件 tag")
    parser.add_argument("--waveform", default="pulse",
                        choices=["pulse", "impulse", "step", "TDR"])
    args = parser.parse_args()

    out_dir = os.path.join(ROOT, "dev_scripts", "diag_out")
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 70)
    print(f"诊断脉冲响应：{os.path.basename(TEST_FILE)}  S{P1},{P2}  waveform={args.waveform}")
    print("=" * 70)

    ntw = rf.Network(TEST_FILE)
    print(f"频率范围 : {ntw.f[0]/1e9:.4f} ~ {ntw.f[-1]/1e9:.2f} GHz   ({len(ntw.f)} 点)")
    df = (ntw.f[-1] - ntw.f[0]) / (len(ntw.f) - 1)
    print(f"df       : {df/1e9:.4f} GHz   (T_total = {1e12/df:.0f} ps)")
    defs = td_default_params(ntw)
    print(f"默认参数 : tr={defs['tr_ps']:.2f}ps  dt={defs['dt_ps']:.4f}ps  "
          f"n_points={defs['n_points']}")

    # 模仿主 UI：新默认 dt=td_default_params['dt_ps']，tr=3*dt，UI宽度=30*dt
    dt_ps = defs["dt_ps"]
    tr_ps = 3 * dt_ps
    pw_ps = 30 * dt_ps
    print(f"调用参数 : tr={tr_ps:.2f}ps  dt={dt_ps:.2f}ps  pw={pw_ps:.2f}ps   (主 UI 新默认)")
    print()

    fig, axes = plt.subplots(len(WINDOWS), 1,
                              figsize=(11, 1.7 * len(WINDOWS)), sharex=True)
    for ax, win in zip(axes, WINDOWS):
        r = compute_time_domain(
            ntw, P1, P2, waveform=args.waveform,
            tr_ps=tr_ps, dt_ps=dt_ps, pulse_width_ps=pw_ps,
            window_type=win,
        )
        t = r["time_ps"]
        y = r["y_data"]
        print(_summary(t, y, label=win))

        ax.plot(t, y, lw=1.0)
        ax.axhline(0, color="gray", lw=0.5, ls="--")
        ax.axvline(t[0], color="red", lw=0.5, ls=":")
        ax.set_ylabel(f"{ZH[win]}\n({win})", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.text(0.99, 0.92, f"y[0]={y[0]:+.3e}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="red")

    axes[-1].set_xlabel("时间 (ps)")
    axes[0].set_title(
        f"{os.path.basename(TEST_FILE)}  S{P1},{P2}  "
        f"{args.waveform}   tr={tr_ps:.1f}ps  dt={dt_ps:.1f}ps  pw={pw_ps:.0f}ps   "
        f"[tag: {args.tag}]"
    )
    plt.tight_layout()
    out_path = os.path.join(out_dir, f"pulse_{args.tag}_{args.waveform}_S{P1}{P2}.png")
    plt.savefig(out_path, dpi=110)
    print()
    print(f"图像已保存: {out_path}")


if __name__ == "__main__":
    main()
