import os

import numpy as np
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)

from app_utils import configure_matplotlib, show_error
from QS_domain.algorithms.topology_detect import detect_topology, format_report


class TopologyDetectDialog(QDialog):
    """拓扑识别与参数矩阵热力图。"""

    def __init__(self, file_names, get_network, parent=None):
        super().__init__(parent)
        self.setWindowTitle("拓扑识别")
        self.resize(680, 460)
        self._file_names = list(file_names)
        self._get_network = get_network
        self._setup_ui()
        self._init_frequency()

    def _setup_ui(self):
        root = QVBoxLayout(self)

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("频点 (GHz):"))
        self._freq_edit = QLineEdit()
        self._freq_edit.setPlaceholderText("例如 0.1")
        freq_row.addWidget(self._freq_edit)
        root.addLayout(freq_row)

        matrix_grp = QGroupBox("参数矩阵热力图")
        matrix_row = QHBoxLayout(matrix_grp)
        self._s_cb = QCheckBox("S参数")
        self._z_cb = QCheckBox("Z参数")
        self._y_cb = QCheckBox("Y参数")
        self._s_cb.setChecked(True)
        self._z_cb.setChecked(True)
        self._y_cb.setChecked(True)
        matrix_row.addWidget(self._s_cb)
        matrix_row.addWidget(self._z_cb)
        matrix_row.addWidget(self._y_cb)
        matrix_row.addStretch()
        root.addWidget(matrix_grp)

        self._summary = QTextEdit()
        self._summary.setReadOnly(True)
        self._summary.setPlaceholderText("点击“执行”后显示拓扑识别结果。")
        root.addWidget(self._summary, stretch=1)

        btn_row = QHBoxLayout()
        run_btn = QPushButton("执行")
        run_btn.clicked.connect(self._run)
        btn_row.addWidget(run_btn)
        btn_row.addStretch()
        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.reject)
        btn_row.addWidget(close_box)
        root.addLayout(btn_row)

    def _init_frequency(self):
        lowest_hz = None
        for file_name in self._file_names:
            try:
                network = self._get_network(file_name)
            except Exception:
                network = None
            if network is None or len(network.f) == 0:
                continue
            f_min = float(np.min(network.f))
            lowest_hz = f_min if lowest_hz is None else min(lowest_hz, f_min)
        if lowest_hz is not None:
            self._freq_edit.setText(f"{lowest_hz / 1e9:.6g}")

    def _selected_param_types(self):
        selected = []
        if self._s_cb.isChecked():
            selected.append("S")
        if self._z_cb.isChecked():
            selected.append("Z")
        if self._y_cb.isChecked():
            selected.append("Y")
        return selected

    def _run(self):
        try:
            freq_ghz = float(self._freq_edit.text())
            if freq_ghz < 0:
                QMessageBox.warning(self, "输入错误", "频点必须大于等于 0。")
                return
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的频点数值。")
            return

        reports = []
        param_types = self._selected_param_types()
        try:
            for file_name in self._file_names:
                network = self._get_network(file_name)
                if network is None:
                    reports.append(f"[拓扑识别] 未找到网络: {file_name}")
                    continue
                if network.nports < 2:
                    reports.append(f"[拓扑识别] {file_name} 端口数 < 2，跳过")
                    continue
                report = detect_topology(network, low_freq_ghz=freq_ghz)
                reports.append(format_report(report, file_label=os.path.basename(file_name)))
                if param_types:
                    self._plot_matrix_heatmaps(network, file_name, freq_ghz, param_types)
            text = "\n\n".join(reports)
            self._summary.setPlainText(text)
            if self.parent() is not None and hasattr(self.parent(), "write"):
                self.parent().write(text + "\n")
        except Exception as exc:
            show_error(self, f"拓扑识别出错: {exc}")

    def _plot_matrix_heatmaps(self, network, file_name: str, freq_ghz: float, param_types: list[str]):
        import matplotlib.pyplot as plt

        configure_matplotlib()
        target_hz = freq_ghz * 1e9
        idx = int(np.abs(network.f - target_hz).argmin())
        actual_ghz = float(network.f[idx] / 1e9)

        ncols = len(param_types)
        fig, axes = plt.subplots(1, ncols, figsize=(4.2 * ncols, 4.2), squeeze=False)
        fig.suptitle(f"{os.path.basename(file_name)}  参数矩阵热力图 @ {actual_ghz:.6g} GHz")

        for ax, param_type in zip(axes[0], param_types):
            matrix = self._param_matrix_at(network, param_type, idx)
            values = np.abs(matrix)
            values = np.ma.array(values, mask=np.triu(np.ones_like(values, dtype=bool)))
            im = ax.imshow(values, cmap="viridis", origin="upper")
            ax.set_title(f"|{param_type}|")
            ax.set_xlabel("端口")
            ax.set_ylabel("端口")
            ticks = np.arange(network.nports)
            labels = [str(i + 1) for i in ticks]
            ax.set_xticks(ticks)
            ax.set_xticklabels(labels)
            ax.set_yticks(ticks)
            ax.set_yticklabels(labels)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        fig.tight_layout()
        fig.show()

    @staticmethod
    def _param_matrix_at(network, param_type: str, idx: int):
        if param_type == "S":
            return network.s[idx]
        if param_type == "Z":
            return network.z[idx]
        if param_type == "Y":
            return network.y[idx]
        raise ValueError(f"未知参数类型: {param_type}")
