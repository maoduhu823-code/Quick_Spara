"""tr 扫描：固定文件 + 端口对，扫 tr ∈ {10,20,35,50} ps × 7 种窗。

横向：tr 值；纵向：窗类型。
"""
import os, sys
import numpy as np
import skrf as rf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
plt.rcParams["font.sans-serif"] = ["SimHei"] if sys.platform == "win32" else ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False

from QS_domain.algorithms.time_domain import compute_time_domain

TEST_FILE = r"C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p"
P1, P2 = 1, 3
WAVEFORM = "pulse"
TR_LIST = [10.0, 20.0, 35.0, 50.0]
DT_PS = 25.0
WINDOWS = ["gaussian", "rect", "hanning", "hamming", "blackman", "tukey", "kaiser"]
ZH = {"gaussian": "高斯", "rect": "矩形", "hanning": "汉宁", "hamming": "汉明",
      "blackman": "布莱克曼", "tukey": "Tukey", "kaiser": "Kaiser"}

ntw = rf.Network(TEST_FILE)
out_dir = os.path.join(ROOT, "dev_scripts", "diag_out")
os.makedirs(out_dir, exist_ok=True)

print(f"扫描 tr × 窗   文件={os.path.basename(TEST_FILE)}  S{P1},{P2}  {WAVEFORM}")
print(f"{'窗':<10s}", end="")
for tr in TR_LIST:
    print(f"   tr={tr:.0f}ps: y[0]   peak    |tail|_rms", end="")
print()
print("-" * (10 + len(TR_LIST) * 35))

XLIM_PS = 800  # 主峰附近
fig, axes = plt.subplots(len(WINDOWS), len(TR_LIST),
                          figsize=(3.8 * len(TR_LIST), 2.0 * len(WINDOWS)),
                          sharex=True, sharey=False)
for i, win in enumerate(WINDOWS):
    print(f"{ZH[win]:<10s}", end="")
    for j, tr in enumerate(TR_LIST):
        r = compute_time_domain(ntw, P1, P2, waveform=WAVEFORM,
                                  tr_ps=tr, dt_ps=DT_PS, window_type=win)
        t = r["time_ps"]; y = r["y_data"]
        n = len(y); tail = y[int(n * 0.85):]
        rms = np.sqrt(np.mean(tail ** 2))
        print(f"   {y[0]:+.3f} {y.max():+.3f} {rms:.3e}", end="")

        ax = axes[i, j]
        ax.plot(t, y, lw=0.9)
        ax.axhline(0, color="gray", lw=0.4, ls="--")
        ax.axvline(0, color="red", lw=0.4, ls=":")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-20, XLIM_PS)
        if i == 0:
            ax.set_title(f"tr={tr:.0f}ps", fontsize=10)
        if j == 0:
            ax.set_ylabel(f"{ZH[win]}\n({win})", fontsize=9)
        ax.text(0.99, 0.95, f"y[0]={y[0]:+.3f}\npeak={y.max():.2f}@{t[np.argmax(y)]:.0f}ps",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="red")
    print()

for ax in axes[-1, :]:
    ax.set_xlabel("时间 (ps)")
fig.suptitle(f"{os.path.basename(TEST_FILE)}  S{P1},{P2}  {WAVEFORM}   "
             f"dt={DT_PS}ps   (横向: tr; 纵向: 窗)",
             fontsize=11)
plt.tight_layout(rect=(0, 0, 1, 0.985))
out_path = os.path.join(out_dir, f"pulse_tr_sweep_S{P1}{P2}.png")
plt.savefig(out_path, dpi=110)
print(f"\n图像已保存: {out_path}")
