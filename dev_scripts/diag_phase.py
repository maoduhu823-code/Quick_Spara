"""分析 S13 的频域相位，判断脉冲应该出现在哪个时间位置。"""
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

TEST_FILE = r"C:/Users/33202/Desktop/HFSS script/StackupDemo1_test.s4p"
ntw = rf.Network(TEST_FILE)
f = ntw.f
s13 = ntw.s[:, 0, 2]

mag = np.abs(s13)
ph_unwrap = np.unwrap(np.angle(s13))
group_delay_ps = -np.gradient(ph_unwrap, f) * 1e12 / (2 * np.pi)

print(f"|S13|     范围: {mag.min():.3f} ~ {mag.max():.3f}")
print(f"|S13| @DC(extrap): {mag[0]:.3f}  @{f[0]/1e9:.2f} GHz")
print(f"|S13| @fmax: {mag[-1]:.3f}  @{f[-1]/1e9:.2f} GHz")
print(f"相位 @{f[0]/1e9:.2f}GHz : {np.degrees(ph_unwrap[0]):+.1f}°")
print(f"相位 @1GHz   : {np.degrees(np.interp(1e9, f, ph_unwrap)):+.1f}°")
print(f"相位 @{f[-1]/1e9:.2f}GHz: {np.degrees(ph_unwrap[-1]):+.1f}°")
print()
print(f"群延迟 (平均): {np.mean(group_delay_ps):.1f} ps")
print(f"群延迟 (中位): {np.median(group_delay_ps):.1f} ps")
print(f"群延迟 (1~10GHz): {np.median(group_delay_ps[(f>=1e9)&(f<=10e9)]):.1f} ps")
print(f"群延迟 (10~30GHz): {np.median(group_delay_ps[(f>=10e9)&(f<=30e9)]):.1f} ps")

# 同时打印 S11 的延迟（TDR 参考）
s11 = ntw.s[:, 0, 0]
print()
print(f"|S11|     范围: {np.abs(s11).min():.3f} ~ {np.abs(s11).max():.3f}")

fig, axes = plt.subplots(3, 1, figsize=(11, 8))
axes[0].plot(f / 1e9, 20 * np.log10(mag + 1e-12), label="|S13|")
axes[0].plot(f / 1e9, 20 * np.log10(np.abs(s11) + 1e-12), label="|S11|", alpha=0.6)
axes[0].set_ylabel("幅度 (dB)")
axes[0].grid(True, alpha=0.4)
axes[0].legend()
axes[0].set_xlim(0, f[-1] / 1e9)

axes[1].plot(f / 1e9, np.degrees(ph_unwrap), label="∠S13 unwrap")
axes[1].set_ylabel("相位 (°)")
axes[1].grid(True, alpha=0.4)
axes[1].legend()
axes[1].set_xlim(0, f[-1] / 1e9)

axes[2].plot(f / 1e9, group_delay_ps, label="S13 群延迟")
axes[2].axhline(np.median(group_delay_ps), ls="--", color="gray",
                label=f"中位={np.median(group_delay_ps):.0f}ps")
axes[2].set_xlabel("频率 (GHz)")
axes[2].set_ylabel("群延迟 (ps)")
axes[2].grid(True, alpha=0.4)
axes[2].legend()
axes[2].set_xlim(0, f[-1] / 1e9)

plt.tight_layout()
out_dir = os.path.join(ROOT, "dev_scripts", "diag_out")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "phase_S13.png")
plt.savefig(out_path, dpi=110)
print()
print(f"图像已保存: {out_path}")
