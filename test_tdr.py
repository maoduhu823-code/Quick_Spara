"""
TDR 算法验证脚本
测试文件: input_test/StackupDemo1_test_renorm_R.s2p
验证目标: TDR 阻抗结果应在 30-100 Ω 合理区间内
"""
import sys, os
import numpy as np
import skrf as rf
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import sys as _sys
plt.rcParams["font.sans-serif"] = ["SimHei"] if _sys.platform == "win32" else ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, os.path.dirname(__file__))
from sparam_core import compute_time_domain, td_default_params

TEST_FILE = os.path.join(os.path.dirname(__file__),
                         "input_test", "StackupDemo1_test_renorm_R.s2p")

ntw = rf.Network(TEST_FILE)
defaults = td_default_params(ntw)

print("=" * 55)
print("TDR 算法验证")
print("=" * 55)
print(f"文件    : {os.path.basename(TEST_FILE)}")
print(f"频率    : {ntw.f[0]/1e9:.4f} ~ {ntw.f[-1]/1e9:.1f} GHz  ({len(ntw.f)} 点)")
print(f"默认参数: tr={defaults['tr_ps']:.1f}ps  dt={defaults['dt_ps']:.1f}ps  "
      f"n={defaults['n_points']}")
print()

# ── 合成已知阻抗剖面验证算法 ──────────────────────────────────────
print("── 合成验证 (已知: 50→100→50Ω) ──")
import skrf as rf2
from skrf.network import Network
Gamma1 = (100 - 50) / (100 + 50)   # +1/3
Gamma2 = (50 - 100) / (50 + 100)   # -1/3
tau1, tau2 = 0.5e-9, 1.0e-9
f_syn = np.linspace(0, 50e9, 501)
s11_syn = (Gamma1 * np.exp(-1j * 4 * np.pi * f_syn * tau1) +
           Gamma2 * np.exp(-1j * 4 * np.pi * f_syn * tau2))
freq_syn = rf2.Frequency.from_f(f_syn, unit="hz")
ntw_syn = rf2.Network(frequency=freq_syn,
                      s=s11_syn.reshape(-1, 1, 1),
                      z0=50.0)
r_syn = compute_time_domain(ntw_syn, 1, 1, "TDR")
t_syn, z_syn = r_syn["time_ps"], r_syn["y_data"]
mask_100 = (t_syn > 800) & (t_syn < 1200)
print(f"  期望 ~100Ω (t=0.8~1.2ns):  实测 [{z_syn[mask_100].min():.1f}, {z_syn[mask_100].max():.1f}] Ω")
passed_syn = z_syn[mask_100].max() > 90.0
print(f"  {'PASS' if passed_syn else 'FAIL'}  (预期 >90Ohm)")

# ── 实测文件 TDR ──────────────────────────────────────────────────
print()
print("── 实测文件 TDR ──")
result = compute_time_domain(ntw, 1, 1, "TDR")
t, z = result["time_ps"], result["y_data"]

z_max = z.max(); z_min = z.min()
t_zmax = t[np.argmax(z)]; t_zmin = t[np.argmin(z)]
print(f"  Z 范围 : {z_min:.1f} ~ {z_max:.1f} Ω")
print(f"  Z 最大 : {z_max:.1f} Ω  @ t = {t_zmax:.0f} ps")
print(f"  Z 最小 : {z_min:.1f} Ω  @ t = {t_zmin:.0f} ps")

in_range = (z_min >= 20) and (z_max <= 150) and (z_min < 45 or z_max > 55)
print(f"  {'PASS' if in_range else 'FAIL'}  (期望: 30~100Ohm 范围内有变化)")

# ── 绘图 ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# 左图：合成验证
ax0 = axes[0]
ax0.plot(t_syn / 1000, z_syn, "b-", lw=1.5)
ax0.axhline(100, color="gray", ls="--", lw=0.8, label="期望 100Ω")
ax0.axhline(50,  color="gray", ls=":",  lw=0.8, label="参考 50Ω")
ax0.set_xlabel("时间 (ns)")
ax0.set_ylabel("阻抗 (Ω)")
ax0.set_title("合成验证：50→100→50Ω")
ax0.legend(fontsize=8)
ax0.set_ylim(30, 120)
ax0.set_xlim(0, t_syn[-1] / 1000)
ax0.grid(True, alpha=0.4)

# 右图：实测文件
ax1 = axes[1]
mask_early = t < 2000   # 只看前 2 ns
ax1.plot(t[mask_early] / 1000, z[mask_early], "r-", lw=1.5)
ax1.axhline(50, color="gray", ls="--", lw=0.8, label="参考 50Ω")
ax1.set_xlabel("时间 (ns)")
ax1.set_ylabel("阻抗 (Ω)")
ax1.set_title(f"TDR: {os.path.basename(TEST_FILE)}\n"
              f"Z [{z_min:.1f}, {z_max:.1f}] Ω")
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.4)

plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(__file__), "test_tdr_result.png"), dpi=120)
print()
print(f"图像已保存: test_tdr_result.png")
plt.show()
