"""一次性验证脚本：用 Twinax line-Spara1G.s4p 跑时域分析对话框，
对比"自动时间窗口"开/关两种情形，并把图保存为 PNG。

用法：
  python dev_scripts/verify_auto_xlim.py

输出：
  dev_scripts/_out/auto_xlim_on.png
  dev_scripts/_out/auto_xlim_off.png
  控制台打印 suggest_time_window 返回值与完整时间轴范围。
"""
import io
import os
import sys

# 强制 UTF-8 输出（避免 Win 控制台 GBK 把中文打成乱码）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# 让 Qt 在无显示器的环境也能跑（PyInstaller / CI / 远程）
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SKRF_PLOT_ENV", "none")

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SAMPLE = os.path.join(ROOT, "samples", "Twinax line-Spara1G.s4p")
OUT_DIR = os.path.join(os.path.dirname(__file__), "_out")


def _setup_app():
    from qtpy.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from app_utils import configure_matplotlib
    configure_matplotlib()
    return app


def _make_viewer_with_file():
    from main_window import SParameterViewer_MainWin
    # 主窗口构造时会把 sys.stdout 重定向到自己的 QTextEdit；先保存再恢复
    _saved_stdout = sys.stdout
    viewer = SParameterViewer_MainWin(enable_time_domain=True)
    sys.stdout = _saved_stdout
    viewer.file_list.addItem(SAMPLE)
    # 触发文件加载到 NetworkService 缓存
    viewer.get_network(SAMPLE)
    # 选中文件
    viewer.file_list.item(0).setSelected(True)
    return viewer


def _open_dialog(viewer):
    from QS_dialogs.time_domain import TimeDomainDialog
    return TimeDomainDialog(
        viewer.s_data, viewer,
        network_service=viewer._net_svc,
        get_selected_files=viewer.get_selected_file_keys,
    )


def _plot_once(viewer, auto_xlim: bool, waveform_key: str,
               p1: int, p2: int, out_png: str) -> tuple:
    """在新对话框里画一次图。返回 (xlim_low, xlim_high)（当前单位）。"""
    dlg = _open_dialog(viewer)
    # 选定 waveform 单选钮
    for btn in dlg._wf_btn_group.buttons():
        if btn.property("wf_key") == waveform_key:
            btn.setChecked(True)
            dlg._on_waveform_changed(btn)
            break
    dlg._auto_xlim_cb.setChecked(auto_xlim)
    dlg._unit_combo.setCurrentText("ns")
    dlg._port1_edit.setText(str(p1))
    dlg._port2_edit.setText(str(p2))
    dlg._clear_port_pairs()
    dlg._add_port_pairs()
    dlg._run_plot()
    # 写出 figure
    if dlg.fig is not None:
        dlg.fig.savefig(out_png, dpi=110, bbox_inches="tight")
        xlim = dlg.ax.get_xlim()
        import matplotlib.pyplot as plt
        plt.close(dlg.fig)
    else:
        xlim = (None, None)
    dlg.close()
    return xlim


def main():
    import matplotlib
    matplotlib.use("Agg")  # 与对话框 QtAgg 不冲突，savefig 走 Agg 即可
    os.makedirs(OUT_DIR, exist_ok=True)

    app = _setup_app()
    viewer = _make_viewer_with_file()
    print(f"sample: {SAMPLE}")

    # 直接对算法跑一次拿数值结果
    from QS_domain.algorithms.time_domain import (
        compute_time_domain, suggest_time_window, td_default_params
    )
    network = viewer.get_network(SAMPLE)
    print(f"端口数 = {network.nports}, 频点数 = {len(network.f)}, "
          f"f_range = {network.f[0] / 1e9:.4f} ~ {network.f[-1] / 1e9:.4f} GHz")
    defaults = td_default_params(network)
    print(f"默认 tr={defaults['tr_ps']} ps, dt={defaults['dt_ps']} ps, "
          f"n={defaults['n_points']}, T_total={defaults['T_total_ps']:.1f} ps "
          f"(= {defaults['T_total_ps'] / 1000:.2f} ns)")

    print("\n-- algorithm only, S21 (port 1 -> port 2) --")
    for wf in ("TDR", "impulse", "step"):
        result = compute_time_domain(network, 1, 2, waveform=wf)
        lo_s, hi_s = suggest_time_window(
            result["impulse_h_t"], result["dt_s"], waveform=wf)
        full_s = result["time_ps"][-1] * 1e-12
        print(f"  [{wf:7s}]  suggest = {lo_s * 1e9:8.3f} ~ {hi_s * 1e9:8.3f} ns   "
              f"(full = 0 ~ {full_s * 1e9:.2f} ns,  "
              f"裁掉 {(1 - (hi_s - lo_s) / full_s) * 100:5.1f}%)")

    print("-- algorithm only, S11 (port 1 -> port 1) --")
    for wf in ("TDR", "impulse"):
        result = compute_time_domain(network, 1, 1, waveform=wf)
        lo_s, hi_s = suggest_time_window(
            result["impulse_h_t"], result["dt_s"], waveform=wf)
        full_s = result["time_ps"][-1] * 1e-12
        peak = float(np.abs(result["impulse_h_t"]).max())
        print(f"  [{wf:7s}]  suggest = {lo_s * 1e9:8.3f} ~ {hi_s * 1e9:8.3f} ns   "
              f"(full = 0 ~ {full_s * 1e9:.2f} ns,  "
              f"裁掉 {(1 - (hi_s - lo_s) / full_s) * 100:5.1f}%,  |h|_peak = {peak:.3e})")

    # 现在让对话框真正画一次（S21 TDR + S21 impulse，单图叠加），分别开/关 auto-xlim
    print("\n[UI] 自动窗口 ON  →  保存到 auto_xlim_on.png")
    xlim_on = _plot_once(viewer, auto_xlim=True, waveform_key="impulse",
                          p1=1, p2=2, out_png=os.path.join(OUT_DIR, "auto_xlim_on.png"))
    print(f"     ax.get_xlim() = {xlim_on[0]:.3f} ~ {xlim_on[1]:.3f} ns")

    print("[UI] 自动窗口 OFF →  保存到 auto_xlim_off.png")
    xlim_off = _plot_once(viewer, auto_xlim=False, waveform_key="impulse",
                           p1=1, p2=2, out_png=os.path.join(OUT_DIR, "auto_xlim_off.png"))
    print(f"     ax.get_xlim() = {xlim_off[0]:.3f} ~ {xlim_off[1]:.3f} ns")

    # TDR S11（同端口）也来一组
    print("[UI] TDR S11 + 自动窗口 ON  →  保存到 tdr_s11_auto_xlim_on.png")
    xlim_tdr_s11 = _plot_once(viewer, auto_xlim=True, waveform_key="TDR",
                           p1=1, p2=1, out_png=os.path.join(OUT_DIR, "tdr_s11_auto_xlim_on.png"))
    print(f"     ax.get_xlim() = {xlim_tdr_s11[0]:.3f} ~ {xlim_tdr_s11[1]:.3f} ns")

    # Step S21
    print("[UI] Step S21 + 自动窗口 ON  →  保存到 step_s21_auto_xlim_on.png")
    xlim_step = _plot_once(viewer, auto_xlim=True, waveform_key="step",
                           p1=1, p2=2, out_png=os.path.join(OUT_DIR, "step_s21_auto_xlim_on.png"))
    print(f"     ax.get_xlim() = {xlim_step[0]:.3f} ~ {xlim_step[1]:.3f} ns")

    viewer.close()
    print("\n完成。PNG 输出目录：", OUT_DIR)


if __name__ == "__main__":
    main()
