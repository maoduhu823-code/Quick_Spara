# Frequency_Analysis2.py
import numpy as np
import pandas as pd
import re
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QLabel, QLineEdit, QMessageBox, QComboBox, QRadioButton,
    QGroupBox, QCheckBox, QGridLayout, QSpinBox, QTextEdit, QStackedWidget, QListWidgetItem, QProgressDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from openpyxl.styles import Alignment
from Basic_function_module import *
import matplotlib

matplotlib.use('Qt5Agg')  # 确保使用Qt5后端


class frequencyAnalysisDialog(QDialog):
    def __init__(self, S_data, s_params_files, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.S_data = S_data
        self.s_params_files = s_params_files
        self.setup_ui()
        # self.plot_lines = []  # 存储绘图线条对象
        # self.current_figure = None  # 当前活动图形
        self.figures = {}  # 格式: {fig_id: {"fig": fig, "lines": [], "cids": []}}
        self.current_fig_id = 0

    def setup_ui(self):
        try:
            self.setWindowTitle("频域分析")
            self.resize(800, 400)

            # 创建复选框组
            self.create_checkboxes()
            # 创建端口排布单选按钮
            port_arrangement_section = self.create_port_arrangement_buttons()
            # 创建串扰和模式单选按钮
            self.create_crosstalk_mode_buttons()
            # 创建频点输入
            self.create_frequency_input()
            # 创建生成按钮
            button_layout = QHBoxLayout()  # 按键水平分布
            self.FrePlot_button = QPushButton("生成图片")
            self.FrePlot_button.clicked.connect(self.generate_plots)
            button_layout.addWidget(self.FrePlot_button)
            self.save_button = QPushButton("导出数据为Excel")
            self.save_button.clicked.connect(self.excel_export)
            button_layout.addWidget(self.save_button)

            # 布局管理
            layout = QVBoxLayout()
            layout.addWidget(self.checkbox_group)
            layout.addWidget(port_arrangement_section)
            layout.addWidget(self.crosstalk_mode_group)
            layout.addWidget(self.frequency_input_group)
            layout.addLayout(button_layout)

            self.setLayout(layout)
        except:
            show_error(self, "绘制曲线时出错")

    def create_checkboxes(self):
        self.checkbox_group = QGroupBox("分析项目")
        self.analysis_checks = {
            'insertion_loss': QCheckBox("插入损耗"),
            'return_loss': QCheckBox("回波损耗"),
            'FarEnd_signal_crosstalk': QCheckBox("远端信号串扰"),
            'NearEnd_signal_crosstalk': QCheckBox("近端信号串扰"),
            'pn_skew': QCheckBox("PN skew"),
            'pn_skew_dev': QCheckBox("PN skew 波动"),
            'pn_mag_mismatch': QCheckBox("PN幅度失配"),
            'group_delay': QCheckBox("群延迟"),
            'FarEnd_XTSum': QCheckBox("远端串扰和"),
            'NearEnd_XTSum': QCheckBox("近端串扰和")
        }

        grid = QGridLayout()
        for i, (key, cb) in enumerate(self.analysis_checks.items()):
            grid.addWidget(cb, i // 4, i % 4)
        self.checkbox_group.setLayout(grid)

    def create_port_arrangement_buttons(self):
        # 创建主容器（水平布局）
        main_container = QWidget()
        layout = QHBoxLayout(main_container)

        # 左侧选项面板（垂直布局）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 端口排布组
        arrangement_group = QGroupBox("端口排布方式")
        self.inside_radio = QRadioButton("按侧排布")
        self.inline_radio = QRadioButton("按线排布")
        self.inside_radio.setChecked(True)
        arrangement_layout = QHBoxLayout()
        arrangement_layout.addWidget(self.inside_radio)
        arrangement_layout.addWidget(self.inline_radio)
        arrangement_group.setLayout(arrangement_layout)

        # 方向组
        direction_group = QGroupBox("传输方向")
        self.forward_radio = QRadioButton("正向")
        self.reverse_radio = QRadioButton("反向")
        self.forward_radio.setChecked(True)
        direction_layout = QHBoxLayout()
        direction_layout.addWidget(self.forward_radio)
        direction_layout.addWidget(self.reverse_radio)
        direction_group.setLayout(direction_layout)

        left_layout.addWidget(arrangement_group)
        left_layout.addWidget(direction_group)
        left_layout.addStretch()

        # 右侧图片显示区（使用堆叠窗口实现切换）
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 创建图片堆叠窗口
        self.image_stack = QStackedWidget()
        self.image_map = {}
        combinations = [
            ("inside_forward", resource_path("resources/按侧排布_正向.PNG")),
            ("inside_reverse", resource_path("resources/按侧排布_反向.PNG")),
            ("inline_forward", resource_path("resources/按线排布_正向.PNG")),
            ("inline_reverse", resource_path("resources/按线排布_反向.PNG"))
        ]

        # 预加载所有图片
        for config_name, img_path in combinations:
            try:
                label = QLabel()
                pixmap = QPixmap(img_path)
                if pixmap.isNull():
                    raise ValueError(f"图片加载失败: {img_path}")

                label.setPixmap(pixmap.scaled(
                    240,
                    180,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))

                self.image_map[config_name] = self.image_stack.addWidget(label)

            except Exception as e:
                error_label = QLabel(f"错误: {str(e)}")
                error_label.setStyleSheet("color: red;")
                self.image_map[config_name] = self.image_stack.addWidget(error_label)

        right_layout.addWidget(self.image_stack)
        right_layout.addStretch()

        # 将左右面板添加到主布局
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        layout.setStretch(0, 2)
        layout.setStretch(1, 2)

        # 连接信号到更新函数
        self.inside_radio.toggled.connect(self.update_image_display)
        self.inline_radio.toggled.connect(self.update_image_display)
        self.forward_radio.toggled.connect(self.update_image_display)
        self.reverse_radio.toggled.connect(self.update_image_display)

        # 初始化显示
        self.update_image_display()

        return main_container

    def update_image_display(self):
        """通过切换堆叠窗口的索引来更新显示"""
        arrangement = "inside" if self.inside_radio.isChecked() else "inline"
        direction = "forward" if self.forward_radio.isChecked() else "reverse"
        config_key = f"{arrangement}_{direction}"

        if config_key in self.image_map:
            self.image_stack.setCurrentIndex(self.image_map[config_key])  # 现在传递的是整数

    def create_crosstalk_mode_buttons(self):
        self.crosstalk_mode_group = QGroupBox("串扰和模式")

        self.power_radio = QRadioButton("功率和")
        self.modulo_radio = QRadioButton("幅度模和")
        self.vector_radio = QRadioButton("幅度矢量和")
        self.power_radio.setChecked(True)

        layout = QHBoxLayout()
        layout.addWidget(self.power_radio)
        layout.addWidget(self.modulo_radio)
        layout.addWidget(self.vector_radio)
        self.crosstalk_mode_group.setLayout(layout)

    def create_frequency_input(self):
        self.frequency_input_group = QGroupBox("关注频点(GHz)")
        self.freG_input = QLineEdit("30")
        self.freG_input.setPlaceholderText("输入频点，多个频点用逗号分隔，如: 1e9, 2e9, 3e9")
        layout = QVBoxLayout()
        layout.addWidget(self.freG_input)
        self.frequency_input_group.setLayout(layout)

    def generate_plots(self):
        # 获取用户选择
        selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
        port_arrangement = "inside" if self.inside_radio.isChecked() else "inline"
        port_direction = "正向" if self.forward_radio.isChecked() else "反向"
        if not selected_options:
            QMessageBox.warning(self, '错误',
                                "请至少选择一个分析项目")
        # # 生成图片
        self.all_results = {}  # dict
        for file2plot in self.s_params_files:
            try:
                network = get_network(self.parent, file2plot)
                # 根据S参数端口数量和排布方式生成port pairs
                num_port = network.nports
                if port_arrangement == 'inside':
                    port_pairs = [(i, i + num_port // 2) for i in range(1, num_port // 2 + 1)]
                else:
                    port_pairs = [(2 * i - 1, 2 * i) for i in range(1, num_port // 2 + 1)]
                a = np.array(port_pairs).T
                port_pairs = a.tolist()
                if port_direction == "反向":
                    port_pairs.reverse()
                # 存储所有结果用于生成表格
                # =========考虑增加反向复选框
                self.file_result = {}  # dict
                for self.option in selected_options:
                    if self.option == 'insertion_loss':
                        plot_mode = "幅度 (dB)"
                        port1_group = port_pairs[1]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(network, port_group, plot_mode, worst_mode="min")
                    elif self.option == 'return_loss':
                        port1_group = port_pairs[0]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(network, port_group)
                    elif self.option == 'FarEnd_signal_crosstalk':
                        port1_group = []
                        port2_group = []
                        for i in range(num_port // 2):
                            p1 = port_pairs[1][i]  # 受害端口
                            for j in range(num_port // 2):
                                # 攻击端口
                                p2 = port_pairs[0][j]
                                if i != j:
                                    port1_group.append(p1)
                                    port2_group.append(p2)
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(network, port_group)
                    elif self.option == 'NearEnd_signal_crosstalk':
                        port1_group = []
                        port2_group = []
                        for i in range(num_port // 2):
                            p1 = port_pairs[0][i]  # 受害端口
                            for j in range(num_port // 2):
                                # 攻击端口
                                p2 = port_pairs[0][j]
                                if i != j:
                                    port1_group.append(p1)
                                    port2_group.append(p2)
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(network, port_group)
                    elif self.option == 'group_delay':
                        plot_mode = "群延迟 (fs)"
                        port1_group = port_pairs[1]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(network, port_group, plot_mode)
                    elif self.option == 'pn_skew':
                        plot_mode = "PN_skew (fs)"
                        self.plot_pn_mismatch(network, port_pairs, plot_mode)
                    elif self.option == 'pn_skew_dev':
                        # 确认公式
                        plot_mode = "PN_skew_dev (fs)"
                        self.plot_pn_mismatch(network, port_pairs, plot_mode)
                    elif self.option == 'pn_mag_mismatch':
                        plot_mode = "PN_Magnitude_Mismatch (dB)"
                        self.plot_pn_mismatch(network, port_pairs, plot_mode)
                    elif self.option == 'FarEnd_XTSum':
                        end_mode = "Far_end"
                        self.plot_s_xtsum(network, port_pairs, end_mode)
                    elif self.option == 'NearEnd_XTSum':
                        end_mode = "Near_end"
                        self.plot_s_xtsum(network, port_pairs, end_mode)

                self.all_results[file2plot] = self.file_result
            except:
                show_error(self, "绘制曲线时出错")

        self.print_results()
        print("✅ Figures plot and Tables print finished")

    def plot_s_curve(self, network, port_group, plot_mode="幅度 (dB)", worst_mode="max"):
        fig, ax = plt.subplots()
        fig_id = self.current_fig_id
        self.current_fig_id += 1
        self.current_figure = fig  # ✅ 避免后续找不到图形

        self.figures[fig_id] = {
            "fig": fig,
            "lines": [],
            "cids": []
        }

        s_params = network.s
        freqG = network.frequency.f / 1e9
        input = self.freG_input.text().split(',')
        mark_freqGs = [float(f.strip()) for f in input if f.strip()]

        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['SimHei']

        ax.set_title(network.name)
        self.mode_result = []

        for p1, p2 in zip(port_group[0], port_group[1]):
            s_param = s_params[:, p1 - 1, p2 - 1]
            if plot_mode == "幅度 (dB)":
                y_data = 20 * np.log10(np.abs(s_param))
            else:
                phase = np.unwrap(np.angle(s_param))
                tau_g = -np.gradient(phase, freqG * 1e9) / (2 * np.pi)
                y_data = tau_g * 1e12  # fs

            if mark_freqGs:
                mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode)
            else:
                mark_info, worst_info = [], []

            label_data = [d['value'] for d in worst_info]
            data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
            label = f'S{p1},{p2}: {data_string}'
            line, = ax.plot(freqG, y_data, label=label, picker=5)
            self.figures[fig_id]["lines"].append(line)

            port_result = {'port': [p1, p2], 'mark_info': mark_info, 'max_info': worst_info}
            self.mode_result.append(port_result)

        for x_line in mark_freqGs:
            ax.axvline(x=x_line, linestyle=':', alpha=1)

        self.file_result[self.option] = self.mode_result
        ax.set_ylabel(self.option)
        ax.set_xlabel("frequency (GHz)")
        ax.grid(True)

        if len(port_group[0]) <= 20:
            legend = ax.legend()
            for text in legend.get_texts():
                text.set_picker(True)  # 让图例文字也可以点击

        cids = [
            fig.canvas.mpl_connect('pick_event', lambda e: self.on_curve_click(e, fig_id)),
            fig.canvas.mpl_connect('button_press_event', lambda e: self.on_click(e, fig_id)),
        ]
        self.figures[fig_id]["cids"] = cids

        fig.show()

    def plot_pn_mismatch(self, network, port_pairs, plot_mode):
        s_params = network.s
        num_port = network.nports
        if num_port % 4 != 0:
            QMessageBox.warning(self, '端口错误', '端口数非4的倍数，请确认是否为差分线的单端S参数')
            return

        input = self.freG_input.text().split(',')
        mark_freqGs = [float(f.strip()) for f in input if f.strip()]

        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['SimHei']

        fig, ax = plt.subplots()
        fig_id = self.current_fig_id
        self.current_fig_id += 1
        self.current_figure = fig

        self.figures[fig_id] = {
            "fig": fig,
            "lines": [],
            "cids": []
        }

        self.mode_result = []

        for i in range(num_port // 4):
            freqG = network.frequency.f / 1e9
            p1, p2 = port_pairs[1][2 * i], port_pairs[0][2 * i]
            p3, p4 = port_pairs[1][2 * i + 1], port_pairs[0][2 * i + 1]
            label = f'Diff{i} (S{p1},{p2} vs S{p3},{p4})'

            if plot_mode == "PN_Magnitude_Mismatch (dB)":
                raw_data1 = 20 * np.log10(np.abs(s_params[:, p1 - 1, p2 - 1]))
                raw_data2 = 20 * np.log10(np.abs(s_params[:, p3 - 1, p4 - 1]))
                y_data = raw_data1 - raw_data2
            else:
                raw_data1 = np.unwrap(np.angle(s_params[:, p1 - 1, p2 - 1]))
                raw_data2 = np.unwrap(np.angle(s_params[:, p3 - 1, p4 - 1]))
                y_data = abs(raw_data1 - raw_data2) * 180 / freqG / 2 * 1e3
                if plot_mode == "PN_skew_dev (fs)":
                    if mark_freqGs:
                        max_mark = np.max(mark_freqGs)
                        mask_skew_dev = (freqG >= 1) & (freqG <= max_mark)
                    else:
                        mask_skew_dev = (freqG >= 1)
                    y_data = y_data[mask_skew_dev]
                    y_mean = sum(y_data) / len(y_data)
                    y_data = y_data - y_mean
                    freqG = freqG[mask_skew_dev]

            mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax)
            label_data = [d['value'] for d in worst_info]
            data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
            line, = ax.plot(freqG, y_data, label=label, picker=5)
            self.figures[fig_id]["lines"].append(line)

            for x_line in mark_freqGs:
                ax.axvline(x=x_line, linestyle=':', alpha=1)

            port_result = {'port': [p1, p2, p3, p4], 'mark_info': mark_info, 'max_info': worst_info}
            self.mode_result.append(port_result)

        ax.set_title(network.name)
        ax.set_xlabel("frequency (GHz)")
        ax.set_ylabel(plot_mode)
        ax.grid(True)
        legend = ax.legend()
        for text in legend.get_texts():
            text.set_picker(True)  # 让图例文字也可以点击

        cids = [
            fig.canvas.mpl_connect('pick_event', lambda e: self.on_curve_click(e, fig_id)),
            fig.canvas.mpl_connect('button_press_event', lambda e: self.on_click(e, fig_id)),
        ]
        self.figures[fig_id]["cids"] = cids

        fig.show()
        self.file_result[self.option] = self.mode_result

    def plot_s_xtsum(self, network, port_pairs, end_mode):
        if self.power_radio.isChecked():
            sum_mode = "Power"
        elif self.modulo_radio.isChecked():
            sum_mode = "Amplitude_Modulo"
        elif self.vector_radio.isChecked():
            sum_mode = "Amplitude_Vector"

        freqG = network.frequency.f / 1e9
        s_params = network.s
        num_port = network.nports
        input = self.freG_input.text().split(',')
        mark_freqGs = [float(f.strip()) for f in input if f.strip()]

        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.sans-serif'] = ['SimHei']

        fig, ax = plt.subplots()
        fig_id = self.current_fig_id
        self.current_fig_id += 1
        self.current_figure = fig

        self.figures[fig_id] = {
            "fig": fig,
            "lines": [],
            "cids": []
        }

        self.mode_result = []

        for i in range(num_port // 2):
            p1 = port_pairs[1][i] if end_mode == "Far_end" else port_pairs[0][i]
            raw_data = np.zeros(len(s_params))
            for j in range(num_port // 2):
                p2 = port_pairs[0][j]
                if i != j:
                    if sum_mode == "Power":
                        raw_data += np.abs(s_params[:, p1 - 1, p2 - 1]) ** 2
                    elif sum_mode == "Amplitude_Modulo":
                        raw_data += np.abs(s_params[:, p1 - 1, p2 - 1])
                    elif sum_mode == "Amplitude_Vector":
                        raw_data += s_params[:, p1 - 1, p2 - 1]
            if sum_mode == "Power":
                y_data = 10 * np.log10(raw_data)
            else:
                y_data = 20 * np.log10(np.abs(raw_data))

            mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax)
            label_data = [d['value'] for d in worst_info]
            data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
            label = f'Line{i + 1}: {data_string}'
            line, = ax.plot(freqG, y_data, label=label, picker=5)
            self.figures[fig_id]["lines"].append(line)

            for x_line in mark_freqGs:
                ax.axvline(x=x_line, linestyle=':', alpha=1)

            port_result = {'port': f'Line{i + 1}', 'mark_info': mark_info, 'max_info': worst_info}
            self.mode_result.append(port_result)

        ax.set_title(network.name)
        ax.set_xlabel("frequency (GHz)")
        ax.set_ylabel(f'{end_mode}_{sum_mode}Sum')
        ax.grid(True)
        legend = ax.legend()
        for text in legend.get_texts():
            text.set_picker(True)  # 让图例文字也可以点击

        cids = [
            fig.canvas.mpl_connect('pick_event', lambda e: self.on_curve_click(e, fig_id)),
            fig.canvas.mpl_connect('button_press_event', lambda e: self.on_click(e, fig_id)),
        ]
        self.figures[fig_id]["cids"] = cids

        fig.show()
        self.file_result[self.option] = self.mode_result


    def on_click(self, event, fig_id):
        if event.dblclick and event.button == 3:  # 右键双击重置
            ax = self.figures[fig_id]["fig"].gca()
            ax.relim()
            ax.autoscale_view()
            self.figures[fig_id]["fig"].canvas.draw()
        elif event.button == 1:  # 左键记录起始位置
            self.last_x, self.last_y = event.xdata, event.ydata

    def on_curve_click(self, event, fig_id):
        fig_data = self.figures[fig_id]
        lines = fig_data["lines"]
        fig = fig_data["fig"]
        ax = fig.gca()

        selected_line = None

        if event.artist in lines:
            selected_line = event.artist  # 曲线本体被点击
        else:
            # 可能是图例文字被点击
            legend = ax.get_legend()
            if legend:
                for text, line in zip(legend.get_texts(), lines):
                    if event.artist == text:
                        selected_line = line
                        break

        if not selected_line:
            return

        # 高亮该曲线，降低其他曲线透明度
        for line in lines:
            line.set_linewidth(3 if line == selected_line else 1)
            line.set_alpha(1.0 if line == selected_line else 0.4)

        # 更新图例文字样式
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                if text.get_text() == selected_line.get_label():
                    text.set_fontweight('bold')
                    text.set_color('red')
                else:
                    text.set_fontweight('normal')
                    text.set_color('black')

        fig.canvas.draw()
        self.print_curve_info(selected_line)

    def highlight_curve(self, selected_line):
        """高亮显示选中的曲线"""
        for line in self.plot_lines:
            line.set_linewidth(1 if line != selected_line else 3)
            line.set_alpha(0.7 if line != selected_line else 1.0)

        # 高亮图例
        ax = selected_line.axes
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                if text.get_text() == selected_line.get_label():
                    text.set_fontweight('bold')
                    text.set_color('red')
                else:
                    text.set_fontweight('normal')
                    text.set_color('black')

    def print_curve_info(self, line):
        """打印曲线信息"""
        info = f"""
        === 曲线信息 ===
        标签: {line.get_label()}
        """
        # X范围: {min(line.get_xdata()):.1f} - {max(line.get_xdata()):.1f} GHz
        # Y范围: {min(line.get_ydata()):.3f} - {max(line.get_ydata()):.3f}
        print(info)

    def reset_view(self):
        """重置图形视图"""
        if self.current_figure:
            ax = self.current_figure.gca()
            ax.relim()
            ax.autoscale_view()
            self.current_figure.canvas.draw()

    def closeEvent(self, event):
        for fig_data in self.figures.values():
            for cid in fig_data["cids"]:
                fig_data["fig"].canvas.mpl_disconnect(cid)
            plt.close(fig_data["fig"])
        super().closeEvent(event)

    def handle_curve_click(self, event):
        """包装器：自动识别 fig_id 并调用 on_curve_click"""
        fig = event.canvas.figure
        for fig_id, fig_data in self.figures.items():
            if fig_data["fig"] == fig:
                self.on_curve_click(event, fig_id)
                break

    def handle_click(self, event):
        """包装器：自动识别 fig_id 并调用 on_click"""
        fig = event.canvas.figure
        for fig_id, fig_data in self.figures.items():
            if fig_data["fig"] == fig:
                self.on_click(event, fig_id)
                break

    def print_results(self):
        """
        在Run窗格打印表格
        """
        try:
            # 获取用户选择
            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            input = self.freG_input.text().split()
            mark_freqGs = list(map(float, input))
            # 按文件处理数据
            for file_name in self.s_params_files:
                file_result = self.all_results[file_name]

                # 在Run窗格打印文件头
                print(f"\n📁 文件: {file_name}")
                print("=" * 60)
                # 按分析模式处理（纵向排列）
                for datamode in selected_options:
                    mode_result = file_result[datamode]
                    # 在Run窗格打印模式头
                    print(f"\n🔍 分析模式: {datamode}")
                    print("-" * 60)
                    # 按频点处理（横向排列）
                    for freq_idx, freq in enumerate(mark_freqGs):
                        table_data = []
                        for item in mode_result:
                            # p1, p2 = item['port']
                            row = [
                                item['port'],
                                round(item['mark_info'][freq_idx].get('value', 0), 3),
                                round(item['max_info'][freq_idx].get('freq', 0), 3),
                                round(item['max_info'][freq_idx].get('value', 0), 3)
                            ]
                            table_data.append(row)
                        # 创建当前频点的DataFrame
                        df = pd.DataFrame(
                            table_data,
                            columns=[
                                f"端口",
                                f"{freq}GHz数据",
                                f"{freq}G内最差频点",
                                f"{freq}G内最差值"
                            ]
                        )
                        # 在Run窗格打印
                        print(f"\n频段: 0~{freq}GHz")
                        print(df.to_string(index=False))
                        print("═" * 40)

        except Exception as e:
            show_error(self, f"打印表格时出错: {str(e)}")

    def excel_export(self):
        """
        导出Excel（优化布局+交互式保存）
        """

        def sanitize_sheet_name(name):
            """清理非法字符，替换为下划线"""
            return re.sub(r'[\\/*?:[\]]', '_', name)[:30]

        def adjust_excel_format(worksheet):
            """调整Excel格式（列宽/行高/居中）"""
            # 列宽自适应
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        # 处理换行文本的宽度计算
                        cell_value = str(cell.value).replace('\n', ' ')
                        max_length = max(max_length, len(cell_value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                worksheet.column_dimensions[column].width = adjusted_width

            # 行高自适应
            for row in worksheet.iter_rows():
                max_lines = 1
                for cell in row:
                    if '\n' in str(cell.value):
                        line_count = len(str(cell.value).split('\n'))
                        max_lines = max(max_lines, line_count)
                if max_lines > 1:
                    worksheet.row_dimensions[row[0].row].height = 15 * max_lines

            # 所有单元格居中
            alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            for row in worksheet.iter_rows():
                for cell in row:
                    cell.alignment = alignment

        try:
            # 弹出文件保存对话框
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存分析结果",
                "Fre_result.xlsx",
                "Excel文件 (*.xlsx);;所有文件 (*)"
            )
            if not file_path:  # 用户取消
                return

            # 确保文件后缀正确
            if not file_path.lower().endswith('.xlsx'):
                file_path += '.xlsx'

            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            input = self.freG_input.text().split()
            mark_freqGs = list(map(float, input))
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for file_name in self.s_params_files:
                    file_result = self.all_results[file_name]
                    main_dfs = []

                    for datamode in selected_options:
                        mode_result = file_result[datamode]

                        # 准备基础数据（端口列）；区分单端、差分、串扰和三种情况的port标题
                        # port_data = [f"S{item['port'][0]}{item['port'][1]}" for item in mode_result]
                        port_data = []
                        for item in mode_result:
                            port = item['port']
                            # 情况1: 直接使用字符串 'LineX'
                            if isinstance(port, str):
                                port_str = port
                            # 情况2: 端口是4个元素的列表 [p1,p2,p3,p4] -> 显示为 S(p1,p2),(p3,p4)
                            elif len(port) == 4:
                                port_str = f"S({port[0]},{port[1]}),({port[2]},{port[3]})"
                            # 情况3: 端口是2个元素的列表 [p1,p2] -> 显示为 Sp1,p2
                            elif len(port) == 2:
                                port_str = f"S{port[0]},{port[1]}"
                            else:
                                port_str = str(port)  # 其他情况直接转为字符串
                            port_data.append(port_str)

                        base_df = pd.DataFrame({"端口": port_data})

                        # 收集所有频点的数据列
                        freq_columns = []

                        for freq_idx, freq in enumerate(mark_freqGs):
                            # 添加当前频点的3列数据
                            freq_data = {
                                f"{freq}GHz数据": [round(item['mark_info'][freq_idx].get('value', 0), 3) for item in
                                                   mode_result],
                                f"{freq}GHz最差频点": [round(item['max_info'][freq_idx].get('freq', 0), 3) for item in
                                                       mode_result],
                                f"{freq}GHz最差值": [round(item['max_info'][freq_idx].get('value', 0), 3) for item in
                                                     mode_result]
                            }
                            freq_columns.append(pd.DataFrame(freq_data))

                        # 合并所有列（端口列+频点数据列）
                        combined_df = pd.concat([base_df] + freq_columns, axis=1)

                        # 添加分析模式标题
                        title_df = pd.DataFrame({
                            "数据类型": [f"{datamode}"]
                        })

                        main_dfs.extend([
                            title_df,
                            combined_df,
                            pd.DataFrame([""])  # 空行分隔
                        ])

                    # 合并所有数据
                    final_df = pd.concat(main_dfs, axis=0)

                    # 写入Excel并调整列宽
                    sheet_name = sanitize_sheet_name(os.path.basename(file_name))
                    final_df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False,
                        header=True
                    )

                    # 获取当前sheet并调整列宽
                    worksheet = writer.sheets[sheet_name]
                    adjust_excel_format(worksheet)

            print(f"\n✅ Excel文件已生成: {file_path}")
        except Exception as e:
            show_error(self, f"导出失败: {str(e)}")