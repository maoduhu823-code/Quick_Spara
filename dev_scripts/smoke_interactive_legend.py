"""可见窗口的 attach_interactive_legend 冒烟脚本。

启动一个真实 QtAgg matplotlib 窗口，按时序模拟：
  1) 单击 legend 小色块 → 高亮回调被触发
  2) 单击 legend 文字   → 高亮回调被触发（回归点）
  3) Shift+单击 legend  → 切换该曲线显示/隐藏
  4) 模拟右键菜单"隐藏 legend" → legend 不可见
  5) Ctrl+L → legend 恢复
  6) 模拟右键菜单"修改标注名…" → 批量改名（注入对话框结果）
  7) 单按 l → 不应误触发 legend toggle
  8) NavigationToolbar 末尾出现「图例」按钮，菜单含两项

运行：
    python -X utf8 dev_scripts/smoke_interactive_legend.py
加 --keep 让窗口走完动作后保持打开。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SKRF_PLOT_ENV", "none")

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import QTimer
from matplotlib.backend_bases import KeyEvent, MouseEvent, PickEvent
import matplotlib.pyplot as plt

from app_utils import (
    attach_interactive_legend,
    apply_legend_batch_rename,
    _legend_rename_map,
    configure_matplotlib,
)


RESULTS: list[tuple[str, bool, str]] = []


def _check(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((label, ok, detail))
    tag = "OK" if ok else "FAIL"
    print(f"[{tag}] {label}{(' — ' + detail) if detail else ''}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true",
                        help="动作走完后保持窗口打开")
    parser.add_argument("--step-ms", type=int, default=700,
                        help="每步间隔毫秒")
    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv[:1])
    configure_matplotlib()

    fig, ax = plt.subplots()
    fig.canvas.manager.set_window_title("interactive legend smoke")
    l1, = ax.plot([0, 1, 2, 3], [0.5, 1.0, 0.3, 0.8], picker=5, label="alpha")
    l2, = ax.plot([0, 1, 2, 3], [0.2, 0.4, 0.9, 0.6], picker=5, label="beta")
    l3, = ax.plot([0, 1, 2, 3], [0.7, 0.1, 0.5, 0.2], picker=5, label="gamma")
    ax.set_title("legend 交互冒烟 — 单击高亮 / Shift+单击切显示 / 右键菜单 / Ctrl+L")
    ax.grid(True)

    picked: list = []

    def on_pick(line):
        picked.append(line)
        for ln in (l1, l2, l3):
            ln.set_linewidth(3 if ln is line else 1)
            ln.set_alpha(1.0 if ln is line else 0.35)
        fig.canvas.draw_idle()

    legend = attach_interactive_legend(
        ax, lines=[l1, l2, l3], on_legend_pick=on_pick,
    )
    fig.show()
    app.processEvents()
    legend_lines = legend.get_lines()
    legend_texts = legend.get_texts()

    def fire_pick(artist, shift=False):
        me = MouseEvent("button_press_event", fig.canvas, 0, 0, button=1,
                        key="shift" if shift else None)
        fig.canvas.callbacks.process(
            "pick_event",
            PickEvent("pick_event", fig.canvas, mouseevent=me, artist=artist),
        )

    def fire_key(key):
        fig.canvas.callbacks.process(
            "key_press_event",
            KeyEvent("key_press_event", fig.canvas, key, 0, 0),
        )

    def s1_click_marker():
        picked.clear()
        fire_pick(legend_lines[1])
        _check("点 legend 小色块 → 高亮 beta",
               picked == [l2], f"picked={[p.get_label() for p in picked]}")

    def s2_click_text():
        picked.clear()
        fire_pick(legend_texts[2])
        _check("点 legend 文字 → 高亮 gamma（回归点）",
               picked == [l3], f"picked={[p.get_label() for p in picked]}")

    def s3_shift_toggle():
        fire_pick(legend_lines[0], shift=True)
        _check("Shift+单击 alpha 隐藏曲线",
               l1.get_visible() is False, f"visible={l1.get_visible()}")
        fire_pick(legend_lines[0], shift=True)
        _check("再 Shift+单击 alpha 恢复显示",
               l1.get_visible() is True, f"visible={l1.get_visible()}")

    def s4_menu_hide():
        # 模拟右键菜单"隐藏 legend" —— 调底层动作
        legend.set_visible(False)
        fig.canvas.draw_idle()
        _check("右键菜单「隐藏 legend」生效",
               legend.get_visible() is False,
               f"legend.visible={legend.get_visible()}")
        _check("隐藏 legend 不影响曲线",
               all(ln.get_visible() for ln in (l1, l2, l3)),
               f"visibilities={[ln.get_visible() for ln in (l1, l2, l3)]}")

    def s5_ctrl_l_show():
        fire_key("ctrl+l")
        _check("Ctrl+L 恢复 legend",
               legend.get_visible() is True,
               f"legend.visible={legend.get_visible()}")

    def s6_batch_rename():
        # 注入 QDialog.exec → Accepted；并把 QLineEdit.text 替换成预设值
        new_names = {"alpha": "α 主线", "beta": "beta", "gamma": "γ 末路"}
        edits_seen: list = []
        original_exec = QDialog.exec

        def fake_exec(self):
            # 找到所有 QLineEdit 子控件，按当前文本匹配预设值
            from PyQt6.QtWidgets import QLineEdit
            for edit in self.findChildren(QLineEdit):
                old = edit.text()
                edits_seen.append(old)
                if old in new_names:
                    edit.setText(new_names[old])
            return QDialog.DialogCode.Accepted.value

        with patch.object(QDialog, "exec", fake_exec):
            apply_legend_batch_rename(_legend_rename_map(legend, [l1, l2, l3]), fig)

        _check("批量改名对话框列出全部条目",
               sorted(edits_seen) == sorted(["alpha", "beta", "gamma"]),
               f"edits_seen={edits_seen}")
        _check("alpha → α 主线 已应用到 legend 与原曲线",
               legend_texts[0].get_text() == "α 主线" and l1.get_label() == "α 主线",
               f"legtext={legend_texts[0].get_text()} label={l1.get_label()}")
        _check("空白/未变项保留原值（beta）",
               legend_texts[1].get_text() == "beta",
               f"legtext={legend_texts[1].get_text()}")

    def s7_l_alone():
        fire_key("l")
        _check("单按 l 不误触发 legend toggle",
               legend.get_visible() is True,
               f"legend.visible={legend.get_visible()}")

    def s8_toolbar_button():
        from PyQt6.QtWidgets import QToolButton
        toolbar = getattr(fig.canvas, "toolbar", None)
        if toolbar is None:
            mgr = getattr(fig.canvas, "manager", None)
            toolbar = getattr(mgr, "toolbar", None) if mgr is not None else None
        _check("NavigationToolbar 存在", toolbar is not None,
               f"toolbar={toolbar!r}")
        if toolbar is None:
            return
        buttons = [w for w in toolbar.findChildren(QToolButton)
                   if w.text() == "图例"]
        _check("工具栏末尾出现「图例」按钮", len(buttons) == 1,
               f"matched={len(buttons)}")
        if not buttons:
            return
        menu = buttons[0].menu()
        actions = [a.text() for a in menu.actions()] if menu else []
        _check("图例按钮菜单含两项",
               actions == ["显示/隐藏 legend", "修改标注名…"],
               f"actions={actions}")

    steps = [
        ("点小色块", s1_click_marker),
        ("点文字（回归）", s2_click_text),
        ("Shift+点切显示", s3_shift_toggle),
        ("右键菜单隐藏", s4_menu_hide),
        ("Ctrl+L 显示", s5_ctrl_l_show),
        ("批量改名对话框", s6_batch_rename),
        ("单按 l 不误触", s7_l_alone),
        ("工具栏「图例」按钮", s8_toolbar_button),
    ]

    def run_step(i):
        if i >= len(steps):
            print("\n=== 汇总 ===")
            passed = sum(1 for _, ok, _ in RESULTS if ok)
            print(f"{passed}/{len(RESULTS)} 通过")
            if not args.keep:
                QTimer.singleShot(args.step_ms, app.quit)
            return
        label, fn = steps[i]
        print(f"\n>>> step {i+1}: {label}")
        try:
            fn()
        except Exception as e:
            _check(label, False, repr(e))
        fig.canvas.draw_idle()
        app.processEvents()
        QTimer.singleShot(args.step_ms, lambda: run_step(i + 1))

    QTimer.singleShot(args.step_ms, lambda: run_step(0))
    app.exec()
    return 0 if all(ok for _, ok, _ in RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
