import os
import sys
import numpy as np
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QRadioButton, QButtonGroup, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox, QTextEdit, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from sparam_core import (compute_time_domain, td_default_params,
                         td_compat_check, parse_port_input)
from app_utils import show_error, check_and_set_port_names
from dialogs.loading import LoadingDialog


# 兼容性状态颜色
_COMPAT_COLOR = {"ok": "#d4edda", "warn": "#fff3cd", "error": "#f8d7da"}
_COMPAT_TEXT  = {"ok": "正常", "warn": "需注意", "error": "风险"}


class TimeDomainDialog(QDialog):
    """
    时域分析对话框。
    从主窗口选中文件 + 端口对输入 → 计算并绘制 TDR / Impulse / Step / Pulse 波形。
    """

    def __init__(self, s_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("时域分析")
        self.resize(900, 680)
        self.s_data = s_data

        self.port_pair_data: dict = {}   # {item_text: {file, p1, p2, waveform}}
        self.all_results: dict   = {}    # {item_text: compute_time_domain 返回值}
        self.fig   = None
        self.ax    = None
        self.td_plot_lines: list = []

        self._compat_timer = QTimer(self)
        self._compat_timer.setSingleShot(True)
        self._compat_timer.timeout.connect(self._update_compat)

        self._setup_ui()
        self._init_param_defaults()

    # ── UI 构建 ─────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)

        root.addWidget(self._build_waveform_group())

        mid = QHBoxLayout()
        mid.addWidget(self._build_params_group(), stretch=3)
        mid.addWidget(self._build_compat_group(), stretch=2)
        root.addLayout(mid)

        root.addWidget(self._build_port_group())
        root.addWidget(self._build_plot_control_group())
        root.addLayout(self._build_bottom_buttons())

    def _build_waveform_group(self):
        grp = QGroupBox("波形类型")
        layout = QHBoxLayout(grp)
        self._wf_btn_group = QButtonGroup(self)
        for i, (label, key) in enumerate([
            ("TDR（阻抗）", "TDR"),
            ("冲激响应", "impulse"),
            ("阶跃响应", "step"),
            ("脉冲响应", "pulse"),
        ]):
            rb = QRadioButton(label)
            rb.setProperty("wf_key", key)
            self._wf_btn_group.addButton(rb, i)
            layout.addWidget(rb)
            if i == 0:
                rb.setChecked(True)

        # 脉冲宽度（仅 pulse 可见）
        self._pw_label = QLabel("脉冲宽度(ps):")
        self._pw_edit  = QLineEdit("100")
        self._pw_edit.setFixedWidth(70)
        self._pw_label.setVisible(False)
        self._pw_edit.setVisible(False)
        layout.addWidget(self._pw_label)
        layout.addWidget(self._pw_edit)
        layout.addStretch()

        self._wf_btn_group.buttonClicked.connect(self._on_waveform_changed)
        return grp

    def _build_params_group(self):
        grp = QGroupBox("时域参数")
        grid = QGridLayout(grp)
        grid.setSpacing(6)

        # tr
        grid.addWidget(QLabel("上升沿 (ps):"), 0, 0)
        self._tr_edit = QLineEdit()
        self._tr_edit.textChanged.connect(lambda: self._compat_timer.start(300))
        grid.addWidget(self._tr_edit, 0, 1)
        btn_tr = QPushButton("自动")
        btn_tr.setFixedWidth(50)
        btn_tr.clicked.connect(lambda: self._on_auto("tr_ps", self._tr_edit))
        grid.addWidget(btn_tr, 0, 2)

        # dt
        grid.addWidget(QLabel("时间步长 (ps):"), 1, 0)
        self._dt_edit = QLineEdit()
        self._dt_edit.textChanged.connect(lambda: self._compat_timer.start(300))
        grid.addWidget(self._dt_edit, 1, 1)
        btn_dt = QPushButton("自动")
        btn_dt.setFixedWidth(50)
        btn_dt.clicked.connect(lambda: self._on_auto("dt_ps", self._dt_edit))
        grid.addWidget(btn_dt, 1, 2)

        # n_points
        grid.addWidget(QLabel("时间点数:"), 2, 0)
        self._n_edit = QLineEdit()
        self._n_edit.textChanged.connect(lambda: self._compat_timer.start(300))
        grid.addWidget(self._n_edit, 2, 1)
        btn_n = QPushButton("自动")
        btn_n.setFixedWidth(50)
        btn_n.clicked.connect(lambda: self._on_auto("n_points", self._n_edit))
        grid.addWidget(btn_n, 2, 2)

        # Z0
        grid.addWidget(QLabel("参考阻抗 Z0 (Ω):"), 3, 0)
        self._z0_edit = QLineEdit("50")
        grid.addWidget(self._z0_edit, 3, 1)

        return grp

    def _build_compat_group(self):
        grp = QGroupBox("兼容性状态")
        layout = QVBoxLayout(grp)
        layout.setSpacing(4)

        font_small = QFont()
        font_small.setPointSize(9)

        self._compat_labels = {}
        for key, text in [("tr", "上升沿"), ("dt", "步长"), ("n", "点数")]:
            lbl = QLabel(f"{text}：正常")
            lbl.setFont(font_small)
            lbl.setStyleSheet(f"background:{_COMPAT_COLOR['ok']};padding:3px;border-radius:3px;")
            lbl.setWordWrap(True)
            self._compat_labels[key] = lbl
            layout.addWidget(lbl)

        self._compat_detail = QTextEdit()
        self._compat_detail.setReadOnly(True)
        self._compat_detail.setFont(font_small)
        self._compat_detail.setFixedHeight(70)
        self._compat_detail.setPlaceholderText("兼容性说明...")
        layout.addWidget(self._compat_detail)
        return grp

    def _build_port_group(self):
        grp = QGroupBox("端口对")
        main = QVBoxLayout(grp)

        top = QHBoxLayout()
        top.addWidget(QLabel("端口1:"))
        self._port1_edit = QLineEdit()
        self._port1_edit.setPlaceholderText("如 1 或 1:4")
        top.addWidget(self._port1_edit)

        top.addWidget(QLabel("端口2:"))
        self._port2_edit = QLineEdit()
        self._port2_edit.setPlaceholderText("如 1（TDR 同端口）")
        top.addWidget(self._port2_edit)

        pick_btn = QPushButton("选择端口名")
        pick_btn.clicked.connect(self._fill_port_by_name)
        top.addWidget(pick_btn)

        top.addWidget(QLabel("映射:"))
        self._map_combo = QComboBox()
        self._map_combo.addItems(["一一对应", "交叉映射"])
        top.addWidget(self._map_combo)
        main.addLayout(top)

        self._port_list = QListWidget()
        self._port_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._port_list.setFixedHeight(100)
        main.addWidget(self._port_list)

        btns = QHBoxLayout()
        for text, slot in [("添加端口对", self._add_port_pairs),
                            ("删除选中",   self._delete_port_pairs),
                            ("清空",       self._clear_port_pairs)]:
            b = QPushButton(text)
            b.setFixedHeight(30)
            b.clicked.connect(slot)
            btns.addWidget(b)
        btns.addStretch()
        main.addLayout(btns)
        return grp

    def _build_plot_control_group(self):
        grp = QGroupBox("绘图控制")
        layout = QHBoxLayout(grp)
        self._same_plot_cb = QCheckBox("曲线叠加")
        self._legend_cb    = QCheckBox("显示图例")
        self._legend_cb.setChecked(True)
        layout.addWidget(self._same_plot_cb)
        layout.addWidget(self._legend_cb)
        layout.addWidget(QLabel("时间单位:"))
        self._unit_combo = QComboBox()
        self._unit_combo.addItems(["ps", "ns"])
        layout.addWidget(self._unit_combo)
        layout.addStretch()
        return grp

    def _build_bottom_buttons(self):
        layout = QHBoxLayout()
        plot_btn = QPushButton("绘 图")
        plot_btn.setFixedHeight(38)
        plot_btn.clicked.connect(self._run_plot)
        layout.addWidget(plot_btn)
        layout.addStretch()
        return layout

    # ── 初始化 ──────────────────────────────────────────────────────────────

    def _init_param_defaults(self):
        networks = list(self.s_data.values())
        if not networks:
            self._tr_edit.setText("50")
            self._dt_edit.setText("5")
            self._n_edit.setText("2048")
            return
        # 取所有网络的保守默认：tr 取最大（最慢），dt 取最大（Nyquist），n_points 取最大
        defaults = [td_default_params(ntw) for ntw in networks]
        tr  = max(d["tr_ps"]    for d in defaults)
        dt  = max(d["dt_ps"]    for d in defaults)
        n   = max(d["n_points"] for d in defaults)
        self._tr_edit.setText(f"{tr:.2f}")
        self._dt_edit.setText(f"{dt:.4f}")
        self._n_edit.setText(str(n))

    # ── 槽函数：波形切换 ─────────────────────────────────────────────────────

    def _on_waveform_changed(self, btn):
        wf = btn.property("wf_key")
        is_pulse = (wf == "pulse")
        self._pw_label.setVisible(is_pulse)
        self._pw_edit.setVisible(is_pulse)
        is_tdr = (wf == "TDR")
        self._z0_edit.setEnabled(is_tdr)
        self._compat_timer.start(300)

    # ── 槽函数：参数自动填充 ─────────────────────────────────────────────────

    def _on_auto(self, field: str, edit: QLineEdit):
        networks = list(self.s_data.values())
        if not networks:
            return
        defaults = [td_default_params(ntw) for ntw in networks]
        if field == "tr_ps":
            val = max(d["tr_ps"]    for d in defaults)
            edit.setText(f"{val:.2f}")
        elif field == "dt_ps":
            val = max(d["dt_ps"]    for d in defaults)
            edit.setText(f"{val:.4f}")
        elif field == "n_points":
            val = max(d["n_points"] for d in defaults)
            edit.setText(str(val))

    # ── 槽函数：兼容性更新 ───────────────────────────────────────────────────

    def _update_compat(self):
        networks = list(self.s_data.values())
        if not networks:
            return
        try:
            tr = float(self._tr_edit.text())
            dt = float(self._dt_edit.text())
            n  = int(self._n_edit.text())
        except ValueError:
            return
        compat = td_compat_check(networks[0], tr, dt, n)
        self._apply_compat_display(compat)

    def _apply_compat_display(self, compat: dict):
        for key in ("tr", "dt", "n"):
            st  = compat[key]
            lbl = self._compat_labels[key]
            name_map = {"tr": "上升沿", "dt": "步长", "n": "点数"}
            lbl.setText(f"{name_map[key]}：{_COMPAT_TEXT[st]}")
            lbl.setStyleSheet(
                f"background:{_COMPAT_COLOR[st]};padding:3px;border-radius:3px;")
        self._compat_detail.setPlainText("\n".join(compat["messages"]) or "各参数与数据兼容。")

    # ── 端口对管理 ───────────────────────────────────────────────────────────

    def _current_waveform(self) -> str:
        checked = self._wf_btn_group.checkedButton()
        return checked.property("wf_key") if checked else "TDR"

    def _fill_port_by_name(self):
        try:
            parent = self.parent()
            file_list = [item.text() for item in parent.file_list.selectedItems()]
            ports = check_and_set_port_names(parent, file_list)
            if ports:
                self._port2_edit.setText(" ".join(map(str, ports)))
        except Exception as e:
            show_error(self, f"选择端口时出错: {str(e)}")

    def _add_port_pairs(self):
        try:
            parent = self.parent()
            selected_files = [item.text() for item in parent.file_list.selectedItems()]
            if not selected_files:
                QMessageBox.warning(self, "提示", "请先在主窗口中选择 S 参数文件")
                return

            p1_text = self._port1_edit.text().strip()
            p2_text = self._port2_edit.text().strip()
            if not p1_text or not p2_text:
                QMessageBox.warning(self, "提示", "请输入端口1和端口2")
                return

            p1_list = parse_port_input(p1_text)
            p2_list = parse_port_input(p2_text)
            if p1_list is None or p2_list is None:
                return

            wf = self._current_waveform()
            mode = self._map_combo.currentText()

            pairs = []
            if mode == "一一对应":
                if len(p1_list) != len(p2_list):
                    QMessageBox.warning(self, "输入错误", "一一对应模式要求两个端口列表数量相同")
                    return
                pairs = list(zip(p1_list, p2_list))
            else:
                pairs = [(p1, p2) for p1 in p1_list for p2 in p2_list]

            for file in selected_files:
                for p1, p2 in pairs:
                    key = f"{os.path.basename(file)}  S{p1},{p2}  [{wf}]"
                    self._port_list.addItem(key)
                    self.port_pair_data[key] = {
                        "file": file, "p1": p1, "p2": p2, "waveform": wf
                    }
        except Exception as e:
            show_error(self, f"添加端口对时出错: {str(e)}")

    def _delete_port_pairs(self):
        for item in self._port_list.selectedItems():
            key = item.text()
            self._port_list.takeItem(self._port_list.row(item))
            self.port_pair_data.pop(key, None)
            self.all_results.pop(key, None)

    def _clear_port_pairs(self):
        self._port_list.clear()
        self.port_pair_data.clear()
        self.all_results.clear()

    # ── 绘图 ─────────────────────────────────────────────────────────────────

    def _run_plot(self):
        if self._port_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加端口对")
            return

        try:
            tr = float(self._tr_edit.text())
            dt = float(self._dt_edit.text())
            n  = int(self._n_edit.text())
            z0 = float(self._z0_edit.text())
        except ValueError:
            QMessageBox.warning(self, "参数错误", "请检查时域参数输入（必须为数字）")
            return

        pw_ps = None
        if self._current_waveform() == "pulse":
            try:
                pw_ps = float(self._pw_edit.text())
            except ValueError:
                pass

        if not self._same_plot_cb.isChecked() or self.fig is None:
            self.fig, self.ax = plt.subplots()
            self.td_plot_lines = []
            if sys.platform == "win32":
                plt.rcParams["font.sans-serif"] = ["SimHei"]
            else:
                plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
            plt.rcParams["axes.unicode_minus"] = False

        unit = self._unit_combo.currentText()

        loading = LoadingDialog(self)
        loading.show()
        QApplication.processEvents()

        last_ylabel = "Impedance (Ω)"
        try:
            for i in range(self._port_list.count()):
                if loading.cancelled:
                    break
                key  = self._port_list.item(i).text()
                info = self.port_pair_data.get(key)
                if info is None:
                    continue

                loading.set_message(f"计算: {key}")
                QApplication.processEvents()

                network = self.s_data.get(info["file"])
                if network is None:
                    print(f"[时域分析] 未找到网络: {info['file']}")
                    continue

                result = compute_time_domain(
                    network, info["p1"], info["p2"],
                    waveform=info["waveform"],
                    tr_ps=tr, dt_ps=dt, n_points=n,
                    z0=z0, pulse_width_ps=pw_ps
                )

                x = result["time_ps"] / 1000 if unit == "ns" else result["time_ps"]

                if self._legend_cb.isChecked():
                    line, = self.ax.plot(x, result["y_data"],
                                         label=result["label"], picker=5)
                else:
                    line, = self.ax.plot(x, result["y_data"], picker=5)

                line.td_result    = result
                line.network_name = info["file"]
                line.port_pair    = (info["p1"], info["p2"])
                line.data_mode    = info["waveform"]
                self.td_plot_lines.append(line)
                self.all_results[key] = result
                last_ylabel = result["y_label"]

            self.ax.set_xlabel(f"时间 ({unit})")
            self.ax.set_ylabel(last_ylabel)
            self.ax.grid(True)
            if self._legend_cb.isChecked():
                self.ax.legend()
            self.fig.canvas.mpl_connect("pick_event", self._on_curve_pick)
            self.fig.show()

        except Exception as e:
            show_error(self, f"绘图时出错: {str(e)}")
        finally:
            loading.close()

    def _on_curve_pick(self, event):
        selected = event.artist
        for line in self.td_plot_lines:
            line.set_linewidth(3 if line is selected else 1)
            line.set_alpha(1.0 if line is selected else 0.4)
        if self.fig:
            self.fig.canvas.draw()
