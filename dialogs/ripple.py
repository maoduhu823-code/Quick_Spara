from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QMessageBox
)

from app_utils import show_error, plot_main_curves, plot_residuals
from sparam_core import ripple_calc, parse_port_input


class RippleFitDialog(QDialog):
    def __init__(self, parent, selected_files):
        super().__init__(parent)
        self.setWindowTitle("Ripple 分析")
        self.setModal(False)
        self.resize(520, 260)
        self.selected_files = selected_files

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 端口输入（参考主界面绘图控制区样式）
        port_grid = QGridLayout()
        port_grid.addWidget(QLabel("端口1:"), 0, 0)
        self.port1_input = QLineEdit()
        self.port1_input.setPlaceholderText("例: 1 2 3 或 1:5")
        port_grid.addWidget(self.port1_input, 0, 1, 1, 3)

        port_grid.addWidget(QLabel("端口2:"), 1, 0)
        self.port2_input = QLineEdit()
        self.port2_input.setPlaceholderText("例: 1:2:5")
        port_grid.addWidget(self.port2_input, 1, 1, 1, 3)

        port_grid.addWidget(QLabel("数据模式:"), 2, 0)
        self.data_mode_combo = QComboBox()
        self.data_mode_combo.addItems([
            "幅度 (dB)", "幅度 (abs)", "相位 (度)", "相位 (rad)",
            "unwrap相位 (度)", "unwrap相位 (rad)", "群延迟 (fs)"
        ])
        port_grid.addWidget(self.data_mode_combo, 2, 1, 1, 3)
        layout.addLayout(port_grid)

        # 频率范围
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("起始频率 (GHz):"))
        self.start_freq_input = QLineEdit("0")
        freq_layout.addWidget(self.start_freq_input)
        freq_layout.addSpacing(10)
        freq_layout.addWidget(QLabel("终止频率 (GHz):"))
        self.stop_freq_input = QLineEdit()
        freq_layout.addWidget(self.stop_freq_input)
        freq_layout.addSpacing(10)
        freq_layout.addWidget(QLabel("频率间隔 (GHz):"))
        self.freq_step_input = QLineEdit("0")
        self.freq_step_input.setEnabled(False)
        freq_layout.addWidget(self.freq_step_input)
        layout.addLayout(freq_layout)

        # 拟合方法 + 动态参数
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("拟合方法:"))
        self.fit_method = QComboBox()
        self.fit_method.addItems(["n次多项式", "IEEE_std_802.3-2022", "平滑函数"])
        self.fit_method.currentTextChanged.connect(self._update_fit_ui)
        method_layout.addWidget(self.fit_method)
        method_layout.addStretch()
        layout.addLayout(method_layout)

        param_grid = QGridLayout()
        self.poly_order_label = QLabel("多项式阶数:")
        self.poly_order_input = QSpinBox()
        self.poly_order_input.setRange(1, 10)
        self.poly_order_input.setValue(5)
        param_grid.addWidget(self.poly_order_label, 0, 0)
        param_grid.addWidget(self.poly_order_input, 0, 1)

        self.ieee_label = QLabel("93A-51公式: a0 + a1·√f + a2·f + a4·f²")
        self.ieee_label.setStyleSheet("color: #666; font-style: italic")
        self.ieee_label.hide()
        param_grid.addWidget(self.ieee_label, 0, 0, 1, 3)

        self.smooth_window_label = QLabel("平滑窗长度:")
        self.smooth_window_input = QSpinBox()
        self.smooth_window_input.setRange(3, 51)
        self.smooth_window_input.setValue(21)
        self.smooth_window_input.setSingleStep(2)
        self.smooth_order_label = QLabel("阶数:")
        self.smooth_order_input = QSpinBox()
        self.smooth_order_input.setRange(1, 5)
        self.smooth_order_input.setValue(3)
        param_grid.addWidget(self.smooth_window_label, 0, 0)
        param_grid.addWidget(self.smooth_window_input, 0, 1)
        param_grid.addWidget(self.smooth_order_label, 0, 2)
        param_grid.addWidget(self.smooth_order_input, 0, 3)
        self.smooth_window_label.hide()
        self.smooth_window_input.hide()
        self.smooth_order_label.hide()
        self.smooth_order_input.hide()
        layout.addLayout(param_grid)

        # 执行按钮
        self.run_btn = QPushButton("执行 Ripple 分析")
        self.run_btn.setFixedHeight(42)
        self.run_btn.clicked.connect(self._run_analysis)
        layout.addWidget(self.run_btn)

        self._update_fit_ui(self.fit_method.currentText())

    def _update_fit_ui(self, method):
        self.poly_order_label.hide()
        self.poly_order_input.hide()
        self.ieee_label.hide()
        self.smooth_window_label.hide()
        self.smooth_window_input.hide()
        self.smooth_order_label.hide()
        self.smooth_order_input.hide()
        if method == "n次多项式":
            self.poly_order_label.show()
            self.poly_order_input.show()
        elif method == "IEEE_std_802.3-2022":
            self.ieee_label.show()
        elif method == "平滑函数":
            self.smooth_window_label.show()
            self.smooth_window_input.show()
            self.smooth_order_label.show()
            self.smooth_order_input.show()

    def _run_analysis(self):
        try:
            port1 = self.port1_input.text().strip()
            port2 = self.port2_input.text().strip()
            start_freq_str = self.start_freq_input.text().strip()
            stop_freq_str = self.stop_freq_input.text().strip()
            method = self.fit_method.currentText()
            data_mode = self.data_mode_combo.currentText()

            if not (port1 and port2 and start_freq_str and stop_freq_str):
                QMessageBox.warning(self, '输入错误', '请填写端口1、端口2、起始频率和终止频率！')
                return

            try:
                port1_list = parse_port_input(port1)
                port2_list = parse_port_input(port2)
                start_freq = float(start_freq_str)
                stop_freq = float(stop_freq_str)
            except (ValueError, TypeError) as e:
                QMessageBox.warning(self, '输入错误', f'参数格式错误: {str(e)}')
                return

            if method == "n次多项式":
                fit_params = {'order': self.poly_order_input.value()}
            elif method == "平滑函数":
                fit_params = {
                    'window_length': self.smooth_window_input.value(),
                    'polyorder': self.smooth_order_input.value()
                }
            else:
                fit_params = {}

            results_data = []
            results_text = []
            parent = self.parent()
            for file_name in self.selected_files:
                try:
                    network = parent.get_network(file_name)
                    s_params = parent.get_param_matrix(file_name, "S参数")
                    for p1, p2 in zip(port1_list, port2_list):
                        if s_params is None or max(p1, p2) > s_params.shape[1]:
                            QMessageBox.warning(self, '端口错误',
                                                f'文件 {file_name} 的端口数不足！')
                            continue
                        result = ripple_calc(network, p1, p2, start_freq, stop_freq,
                                             data_mode, method, fit_params, s_params=s_params)
                        results_data.append(result)
                        results_text.append(
                            f"{result['label']}: ripple = {result['max_ripple']:.4f}")
                except Exception as e:
                    show_error(self, f"处理文件 {file_name} 时出错: {str(e)}")

            if results_data:
                plot_main_curves(results_data, data_mode)
                plot_residuals(results_data, data_mode)
                print('\nRipple 分析结果:')
                for text in results_text:
                    print(text)
            else:
                QMessageBox.warning(self, '无结果', '没有生成任何有效结果！')
        except Exception:
            show_error(self, "Ripple 分析执行出错")
