# Frequency_Analysis.py
import sys

import numpy as np
import pandas as pd
import re
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QListWidget, QLabel, QLineEdit, QMessageBox, QComboBox, QRadioButton,
    QGroupBox, QCheckBox, QGridLayout, QSpinBox, QTextEdit, QStackedWidget, QListWidgetItem, QProgressDialog,
    QSizePolicy
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from openpyxl.styles import Alignment
import matplotlib
import matplotlib.patches as mpatches

from app_utils import show_error, resource_path, freq_band_data_extract
from sparam_core import parse_port_input


OPTION_META = {
    'insertion_loss': ('插入损耗', 'dB'),
    'return_loss': ('回波损耗', 'dB'),
    'FarEnd_signal_crosstalk': ('远端信号串扰', 'dB'),
    'NearEnd_signal_crosstalk': ('近端信号串扰', 'dB'),
    'pn_skew': ('PN skew', 'fs'),
    'pn_skew_dev': ('PN skew 波动', 'fs'),
    'pn_mag_mismatch': ('PN 幅度失配', 'dB'),
    'group_delay': ('群延迟', 'fs'),
    'FarEnd_XTSum': ('远端串扰和', 'dB'),
    'NearEnd_XTSum': ('近端串扰和', 'dB'),
    'VTF_loss': ('VTF 损耗', 'dB'),
    'VTF_XTSum': ('VTF 串扰和', 'dB'),
}


def option_display_name(option):
    return OPTION_META.get(option, (option, ''))[0]


def option_unit(option):
    return OPTION_META.get(option, ('', ''))[1]


def option_axis_label(option):
    name, unit = OPTION_META.get(option, (option, ''))
    return f"{name} ({unit})" if unit else name


class frequencyAnalysisDialog(QDialog):
    def __init__(self, S_data, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.S_data = S_data
        self.s_params_files = []
        self.setup_ui()
        # self.plot_lines = []  # 存储绘图线条对象
        # self.current_figure = None  # 当前活动图形
        self.figures = {}  # 格式: {fig_id: {"fig": fig, "lines": [], "cids": []}}
        self.current_fig_id = 0
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        if sys.platform == 'win32':
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 仅影响普通文本
            plt.rcParams['mathtext.fontset'] = 'stix'  # 仅影响数学符号
        else:
            plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # 仅影响普通文本

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
            button_layout.setSpacing(5)  # 设置控件之间的间距为5像素

            # 创建标签和输入框的容器
            label_input_container = QWidget()
            label_input_layout = QHBoxLayout(label_input_container)
            label_input_layout.setContentsMargins(0, 0, 0, 0)  # 移除内边距
            label_input_layout.setSpacing(2)  # 设置标签和输入框之间的小间距
            # 添加标签和输入框
            port_label = QLabel("输入line序号:")
            port_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # 固定大小
            label_input_layout.addWidget(port_label)
            self.line_input = QLineEdit('1')
            self.line_input.setFixedWidth(80)
            self.line_input.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # 固定大小
            label_input_layout.addWidget(self.line_input)

            # 将标签和输入框容器添加到主按钮布局
            button_layout.addWidget(label_input_container)
            self.specific_line_button = QPushButton("指定line绘制")
            self.specific_line_button.clicked.connect(self.generate_specific_line_waveforms)
            button_layout.addWidget(self.specific_line_button)
            self.compare_button = QPushButton("最差line绘制")
            self.compare_button.clicked.connect(self.generate_comparison_waveforms)
            button_layout.addWidget(self.compare_button)
            self.bar_button = QPushButton("柱状图-横向比较")  # 新增按钮2
            self.bar_button.clicked.connect(self.generate_comparison_bars)
            button_layout.addWidget(self.bar_button)
            self.FrePlot_button = QPushButton("按文件绘制")
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
            'NearEnd_XTSum': QCheckBox("近端串扰和"),
            'VTF_loss': QCheckBox("VTF_损耗"),
            'VTF_XTSum': QCheckBox("VTF_串扰和"),
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
            ("inside_forward", resource_path("resources/inside_posi.PNG")),
            ("inside_reverse", resource_path("resources/inside_nega.PNG")),
            ("inline_forward", resource_path("resources/inline_posi.PNG")),
            ("inline_reverse", resource_path("resources/inline_nega.PNG"))
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
        self.freG_input.setPlaceholderText("输入频点，多个频点用逗号分隔，如: 10, 20, 30")
        layout = QVBoxLayout()
        layout.addWidget(self.freG_input)
        self.frequency_input_group.setLayout(layout)

    def _get_s_params(self, file_name, network):
        if self.parent and hasattr(self.parent, "get_param_matrix"):
            return self.parent.get_param_matrix(file_name, "S参数")
        return network.s

    def generate_specific_line_waveforms(self):
        """将所有S参数文件中用户指定的bit波形绘制在同一张图中"""
        try:
            self.s_params_files = self.parent.get_selected_file_keys()
            if not self.s_params_files:
                QMessageBox.warning(self, '错误', '请先选择需要进行频域分析的S参数文件！')
                return
            # 获取用户选择的线号
            line_input = self.line_input.text().strip()
            if not line_input:
                QMessageBox.warning(self, '错误', "请输入要绘制的线号")
                return

            try:
                specified_lines = [int(x.strip()) for x in line_input.split(',')]
                if not specified_lines:
                    QMessageBox.warning(self, '错误', "请输入有效的线号")
                    return
            except ValueError:
                QMessageBox.warning(self, '错误', "线号格式不正确，请使用逗号分隔的数字（如1,2,3）")
                return

            # 获取其他参数
            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            port_arrangement = "inside" if self.inside_radio.isChecked() else "inline"
            port_direction = "正向" if self.forward_radio.isChecked() else "反向"
            input = self.freG_input.text()
            mark_freqGs = parse_port_input(input, type="freq")

            if not selected_options:
                QMessageBox.warning(self, '错误', "请至少选择一个分析项目")
                return

            # 存储所有结果用于生成表格
            self.all_results = {}

            # 为每个分析项目创建图表
            for i, option in enumerate(selected_options):
                fig = plt.figure(figsize=(6, 5))
                self.current_fig_id += 1
                fig_id = self.current_fig_id

                ax = fig.add_subplot(111)
                self.figures[fig_id] = {"fig": fig, "lines": [], "cids": []}
                # 设置图片在屏幕上的位置，实现一字排开
                # 将图片水平排列，每个图片向右偏移
                position_x = i % 4 * (6 * 100)  # 100是DPI的近似值，调整这个值来控制间距
                position_y = i // 4 * (2 * 100) + 20
                manager = plt.get_current_fig_manager()
                manager.window.move(position_x, position_y)  # 水平排列，垂直位置固定为100

                # 初始化 all_results 结构
                if not hasattr(self, 'all_results'):
                    self.all_results = {}  # 结构: {option: {file_path: [result1, result2...]}}
                if option not in self.all_results:
                    self.all_results[option] = {}

                # 处理每个文件
                for file_idx, file2plot in enumerate(self.s_params_files):
                    network = self.parent.get_network(file2plot)
                    num_port = network.nports
                    file_name = os.path.basename(file2plot)
                    # 初始化当前文件的结果列表
                    if file2plot not in self.all_results[option]:
                        self.all_results[option][file2plot] = []

                    # 生成端口对
                    port_pairs = [(i, i + num_port // 2) for i in
                                  range(1, num_port // 2 + 1)] if port_arrangement == 'inside' \
                        else [(2 * i - 1, 2 * i) for i in range(1, num_port // 2 + 1)]

                    port_pairs = np.array(port_pairs).T.tolist()
                    if port_direction == "反向":
                        port_pairs.reverse()

                    # 绘制每条指定线号的曲线
                    for line_num in specified_lines:
                        if line_num < 1 or line_num > len(port_pairs[0]):
                            continue  # 跳过无效线号

                        # 获取端口对
                        port_pair = (port_pairs[0][line_num - 1], port_pairs[1][line_num - 1])
                        result = None
                        # 获取数据并绘制曲线
                        if option in ['insertion_loss', 'VTF_loss']:
                            port_group = [[port_pair[1]], [port_pair[0]]]
                            result = self.plot_s_curve_specific(network, port_group, option, ax, file2plot, line_num,
                                                       mark_freqGs, worst_mode='min')
                        elif option == 'return_loss':
                            port_group = [[port_pair[0]], [port_pair[0]]]
                            result = self.plot_s_curve_specific(network, port_group, option, ax, file2plot, line_num,
                                                       mark_freqGs)
                        elif option == 'FarEnd_signal_crosstalk':
                            # 远端串扰需要特殊处理端口组
                            port_group = [[], []]
                            for j in range(len(port_pairs[0])):
                                if j != line_num - 1:  # 排除自身
                                    port_group[0].append(port_pairs[1][line_num - 1])  # 受害端口
                                    port_group[1].append(port_pairs[0][j])  # 攻击端口
                            result = self.plot_s_curve_specific(network, port_group, option, ax, file2plot, line_num,
                                                       mark_freqGs)
                        elif option == 'NearEnd_signal_crosstalk':
                            # 近端串扰需要特殊处理端口组
                            port_group = [[], []]
                            for j in range(len(port_pairs[0])):
                                if j != line_num - 1:  # 排除自身
                                    port_group[0].append(port_pairs[0][line_num - 1])  # 受害端口
                                    port_group[1].append(port_pairs[0][j])  # 攻击端口
                            result = self.plot_s_curve_specific(network, port_group, option, ax, file2plot, line_num,
                                                       mark_freqGs)
                        elif option == 'group_delay':
                            port_group = [[port_pair[1]], [port_pair[0]]]
                            result = self.plot_s_curve_specific(network, port_group, option, ax, file2plot, line_num,
                                                       mark_freqGs, "群延迟 (fs)")
                        elif option in ['FarEnd_XTSum', 'NearEnd_XTSum', 'VTF_XTSum']:
                            result = self.plot_xtsum_specific(network, port_pairs, option, ax, file2plot, line_num, mark_freqGs)
                        elif option in ['pn_skew', 'pn_skew_dev', 'pn_mag_mismatch']:
                            # 对于差分线指标，需要找到对应的差分对
                            if line_num <= num_port // 4:
                                result = self.plot_pn_mismatch_specific(network, port_pairs, option, ax, file2plot, line_num,
                                                               mark_freqGs)
                        # print(result)
                        if result:
                            # 对于串扰情况，处理多个结果
                            if 'all_results' in result:
                                # 结构化存储所有结果
                                full_results = []
                                # print(result['all_results'])
                                for i, single_result in enumerate(result['all_results']):
                                    full_results.append({
                                        'file_name': file_name,
                                        'line_num': line_num,
                                        'port': single_result['port'],
                                        'mark_info': single_result['mark_info'],
                                        'max_info': single_result['max_info'],
                                        'raw_data': single_result.get('raw_data')
                                    })
                                    # print(single_result)
                            else:
                                # 非串扰情况的处理（保持原样）
                                full_results = {
                                    'file_name': file_name,
                                    'line_num': line_num,
                                    'port': result['port'],
                                    'mark_info': result['mark_info'],
                                    'max_info': result['max_info'],
                                    'raw_data': result.get('raw_data')
                                }
                            self.all_results[option][file2plot].append(full_results)


                # 添加频点标记线
                for freq in mark_freqGs:
                    ax.axvline(x=freq, linestyle=':', color='gray', alpha=0.7)

                # 设置图表属性
                ax.set_title(f"{option_display_name(option)} - bit {','.join(map(str, specified_lines))}比较")
                ax.set_xlabel("Frequency (GHz)")
                ax.set_ylabel(option_axis_label(option))
                ax.legend(loc='best')
                ax.grid(True)

                # 添加交互功能
                def make_on_click(fid):
                    return lambda e: self.on_click(e, fid)

                def make_on_pick(fid):
                    return lambda e: self.on_curve_click(e, fid)

                cids = [
                    fig.canvas.mpl_connect('button_press_event', make_on_click(fig_id)),
                    fig.canvas.mpl_connect('pick_event', make_on_pick(fig_id)),
                ]
                self.figures[fig_id]["cids"] = cids

                fig.tight_layout()
                fig.show()

            # print(self.all_results)
            self.print_comparison_results(mode="specific")
            print("✅ 指定线号曲线绘制完成")

        except Exception as e:
            show_error(self, f"生成指定线号曲线图时出错: {str(e)}")

    def plot_s_curve_specific(self, network, port_group, option, ax, file_name, line_num, mark_freqGs,
                              plot_mode="幅度 (dB)", worst_mode="max"):
        """绘制指定线号的S参数曲线"""
        s_params = self._get_s_params(file_name, network)
        freqG = network.frequency.f / 1e9
        results = []  # 用于存储所有端口对的结果

        for p1, p2 in zip(port_group[0], port_group[1]):
            s_param = s_params[:, p1 - 1, p2 - 1]
            # 如果是打印VTF变量，则需要增加一步处理
            if option == 'VTF_loss':
                z0 = network.z0
                z_source = z0[:, p2 - 1]
                z_load = z0[:, p1 - 1]
                # print(f'低频比例：port{p1-1}/port{p2-1}={abs(z_load[0] / z_source[0])}')
                # print(f'高频比例：port{p1-1}/port{p2-1}={abs(z_load[-1] / z_source[-1])}')
                s_param = 0.5 * s_param * np.sqrt(z_load / z_source)  # 这里不再该变量名了，但是实际上是VTF了

            if plot_mode == "幅度 (dB)":
                y_data = 20 * np.log10(np.abs(s_param))
            elif plot_mode == "群延迟 (fs)":
                phase = np.unwrap(np.angle(s_param))
                tau_g = -np.gradient(phase, freqG * 1e9) / (2 * np.pi)
                y_data = tau_g * 1e15  # fs
            else:
                return None

            # 计算关注频点数据
            mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode)

            # 生成标签
            label_data = [d['value'] for d in worst_info]
            data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
            label = f"{os.path.basename(file_name)} 线{line_num}(S{p1},{p2}): {data_string}"

            # 绘制曲线
            line, = ax.plot(freqG, y_data, label=label, picker=5)
            self.figures[self.current_fig_id]["lines"].append(line)
            # 保存当前端口对的结果
            results.append({
                'port': (p1, p2),
                'mark_info': mark_info,
                'max_info': worst_info,
                'raw_data': y_data  # 可选：保存原始数据
            })

        # 对于串扰情况，返回所有端口对的结果
        if option in ['NearEnd_signal_crosstalk', 'FarEnd_signal_crosstalk']:
            return {
                'line_num': line_num,
                'all_results': results,  # 包含所有端口对的结果
                'port': [p[0] for p in port_group],  # 返回所有端口信息
                'mark_info': [r['mark_info'] for r in results],  # 所有mark信息
                'max_info': [r['max_info'] for r in results]  # 所有worst信息
            }
        else:
            # 对于非串扰情况，保持原有返回格式（取第一个结果）
            return {
                'line_num': line_num,
                'port': results[0]['port'] if results else None,  # 取第一个端口对
                'mark_info': results[0]['mark_info'] if results else None,
                'max_info': results[0]['max_info'] if results else None,
                'raw_data': results[0]['raw_data'] if results else None
            }
    def plot_xtsum_specific(self, network, port_pairs, option, ax, file_name, line_num, mark_freqGs):
        """绘制指定线号的串扰和曲线"""
        s_params = self._get_s_params(file_name, network)
        freqG = network.frequency.f / 1e9
        num_port = network.nports

        # 确定求和模式
        if self.power_radio.isChecked():
            sum_mode = "Power"
        elif self.modulo_radio.isChecked():
            sum_mode = "Amplitude_Modulo"
        elif self.vector_radio.isChecked():
            sum_mode = "Amplitude_Vector"
        else:
            sum_mode = "Power"

        # 确定是远端还是近端
        end_mode = "Far_end" if option in ["FarEnd_XTSum", "VTF_XTSum"] else "Near_end"

        # 获取当前线号的接收端口
        if end_mode == "Far_end":
            p1 = port_pairs[1][line_num - 1]
            other_ports = [port_pairs[0][j] for j in range(num_port // 2) if j != line_num - 1]
        else:
            p1 = port_pairs[0][line_num - 1]
            other_ports = [port_pairs[0][j] for j in range(num_port // 2) if j != line_num - 1]
        print(f'rx port: {p1}')
        print(f'tx port: {other_ports}')
        # 计算串扰和
        raw_data = np.zeros(len(s_params), dtype=np.complex128)
        for p2 in other_ports:
            if option == "VTF_XTSum":
                z0 = network.z0
                z_source = z0[:, p2 - 1]
                z_load = z0[:, p1 - 1]
                vtf_ratio = 0.5 * np.sqrt(z_load / z_source)
                raw_data += np.abs(vtf_ratio * s_params[:, p1 - 1, p2 - 1]) ** 2
            else:
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

        # 计算关注频点数据
        mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax)

        # 生成标签
        label_data = [d['value'] for d in worst_info]
        data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
        label = f"{os.path.basename(file_name)} 线{line_num}({option}): {data_string}"

        # 绘制曲线
        line, = ax.plot(freqG, y_data, label=label, picker=5)
        self.figures[self.current_fig_id]["lines"].append(line)
        return {
            'line_num': line_num,
            'port': (p1, p2),  # 取第一个端口对
            'mark_info': mark_info,
            'max_info': worst_info
        }

    def plot_pn_mismatch_specific(self, network, port_pairs, option, ax, file_name, line_num, mark_freqGs):
        """绘制指定差分对的PN不匹配曲线"""
        s_params = self._get_s_params(file_name, network)
        freqG = network.frequency.f / 1e9
        freq = network.frequency.f

        # 获取差分对端口
        p1 = port_pairs[1][2 * (line_num - 1)]
        p2 = port_pairs[0][2 * (line_num - 1)]
        p3 = port_pairs[1][2 * (line_num - 1) + 1]
        p4 = port_pairs[0][2 * (line_num - 1) + 1]

        if option == 'pn_mag_mismatch':
            raw_data1 = 20 * np.log10(np.abs(s_params[:, p1 - 1, p2 - 1]))
            raw_data2 = 20 * np.log10(np.abs(s_params[:, p3 - 1, p4 - 1]))
            y_data = raw_data1 - raw_data2
            plot_mode = "PN_Magnitude_Mismatch (dB)"
        else:
            raw_data1 = np.unwrap(np.angle(s_params[:, p1 - 1, p2 - 1]))
            raw_data2 = np.unwrap(np.angle(s_params[:, p3 - 1, p4 - 1]))
            y_data = abs(raw_data1 - raw_data2) / (2 * np.pi * freqG) * 1e6

            if option == 'pn_skew_dev':
                if mark_freqGs:
                    max_mark = np.max(mark_freqGs)
                    mask_skew_dev = (freqG >= 1) & (freqG <= max_mark)
                else:
                    mask_skew_dev = (freqG >= 1)
                y_data = y_data[mask_skew_dev]
                y_mean = sum(y_data) / len(y_data)
                y_data = y_data - y_mean
                freqG = freqG[mask_skew_dev]
                plot_mode = "PN_skew_dev (fs)"
            else:
                plot_mode = "PN_skew (fs)"

        # 计算关注频点数据
        mark_info, worst_info = freq_band_data_extract(mark_freqGs, freqG, y_data, ax)

        # 生成标签
        label_data = [d['value'] for d in worst_info]
        data_string = ', '.join(['{:.3f}'.format(d) for d in label_data])
        label = f"{os.path.basename(file_name)} 差分对{line_num}({option}): {data_string}"

        # 绘制曲线
        line, = ax.plot(freqG, y_data, label=label, picker=5)
        print(line)
        self.figures[self.current_fig_id]["lines"].append(line)
        return {
            'line_num': line_num,
            'port': (p1, p2),  # 取第一个端口对
            'mark_info': mark_info,
            'max_info': worst_info
        }

    def generate_comparison_waveforms(self):
        """生成最差曲线比较图，并确保数据打印和legend格式统一"""
        try:
            # 获取用户选择
            self.s_params_files = self.parent.get_selected_file_keys()
            if not self.s_params_files:
                QMessageBox.warning(self, '错误', '请先选择需要进行频域分析的S参数文件！')
                return
            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            port_arrangement = "inside" if self.inside_radio.isChecked() else "inline"
            port_direction = "正向" if self.forward_radio.isChecked() else "反向"
            mark_freqGs = parse_port_input(self.freG_input.text(), type="freq")

            if not selected_options:
                QMessageBox.warning(self, '错误', "请至少选择一个分析项目")
                return

            # 过滤不支持比较的选项
            valid_options = [opt for opt in selected_options
                             if opt not in ['pn_skew', 'pn_skew_dev', 'pn_mag_mismatch', 'group_delay']]
            if not valid_options:
                QMessageBox.warning(self, '错误', "没有可比较的有效指标")
                return

            # 初始化数据结构
            self.all_results = {}  # 结构: {option: {file_path: [result_dict]}}
            self.comparison_bar_data = {freq: [] for freq in mark_freqGs}
            for i, option in enumerate(valid_options):
                fig = plt.figure(figsize=(6, 5))
                self.current_fig_id += 1
                fig_id = self.current_fig_id

                ax = fig.add_subplot(111)
                self.figures[fig_id] = {"fig": fig, "lines": [], "cids": []}
                # 设置图片在屏幕上的位置，实现一字排开
                # 将图片水平排列，每个图片向右偏移
                position_x = i % 4 * (6 * 100)  # 100是DPI的近似值，调整这个值来控制间距
                position_y = i // 4 * (2 * 100) + 20
                manager = plt.get_current_fig_manager()
                manager.window.move(position_x, position_y)  # 水平排列，垂直位置固定为100
                self.all_results[option] = {}  # 初始化当前option的数据结构

                for file_path in self.s_params_files:
                    network = self.parent.get_network(file_path)
                    num_port = network.nports
                    short_name = os.path.basename(file_path)

                    # 生成端口对
                    if port_arrangement == 'inside':
                        port_pairs = [(i, i + num_port // 2) for i in range(1, num_port // 2 + 1)]
                    else:
                        port_pairs = [(2 * i - 1, 2 * i) for i in range(1, num_port // 2 + 1)]

                    port_pairs = np.array(port_pairs).T.tolist()
                    if port_direction == "反向":
                        port_pairs.reverse()

                    # 获取最差曲线数据(曲线绘图数据也是从这里来）
                    worst_data = self.get_worst_bit_data(file_path, network, option, port_pairs, mark_freqGs)
                    # print(worst_data)
                    if not worst_data:
                        continue

                    # 生成legend标签（包含数据）
                    label_data = [f"{v:.3f}" for v in worst_data['max_values']]
                    data_string = ', '.join(label_data)
                    label = f"{short_name} ({worst_data['port']}): {data_string}"

                    # 绘制曲线（使用统一格式的label）
                    line, = ax.plot(
                        worst_data['freqG'],
                        np.real(worst_data['y_data']),
                        label=label,
                        picker=5
                    )
                    self.figures[fig_id]["lines"].append(line)

                    # 存储结构化结果
                    result = {
                        'file_name': short_name,
                        'line_num': worst_data['line'],  # 标记为最差曲线
                        'port': worst_data['port'],
                        'mark_info': [{'value': v} for v in worst_data['mark_values']],
                        'max_info': [{'freq': f, 'value': v}
                                     for f, v in zip(worst_data['freq_at_max'],
                                                     worst_data['max_values'])]
                    }
                    # print(result)
                    self.all_results[option][file_path] = [result]

                    # 存储柱状图数据（保持原结构不变）
                    for i, freq in enumerate(mark_freqGs):
                        self.comparison_bar_data[freq].append({
                            'option': option,
                            'value': float(np.real(worst_data['max_values'][i])),
                            'file': short_name,
                            'color': line.get_color(),
                            'freq_at_max': float(np.real(worst_data['freq_at_max'][i]))
                        })

                # 图表装饰
                for freq in mark_freqGs:
                    ax.axvline(x=freq, linestyle=':', color='gray', alpha=0.7)

                ax.set_title(f"{option_display_name(option)} - 最差曲线比较")
                ax.set_xlabel("Frequency (GHz)")
                ax.set_ylabel(option_axis_label(option))
                ax.grid(True)
                ax.legend()  # 显示包含数据的图例

                # 交互功能
                cid1 = fig.canvas.mpl_connect(
                    'button_press_event',
                    lambda e, fid=fig_id: self.on_click(e, fid))
                cid2 = fig.canvas.mpl_connect(
                    'pick_event',
                    lambda e, fid=fig_id: self.on_curve_click(e, fid))
                self.figures[fig_id]["cids"] = [cid1, cid2]

                fig.tight_layout()
                fig.show()

            # 打印结果（使用统一打印函数）
            self.print_comparison_results(mode="comparison")
            print("✅ 最差曲线比较完成")

        except Exception as e:
            show_error(self, f"生成比较曲线时出错: {str(e)}")

    def generate_comparison_bars(self):
        try:
            if not hasattr(self, "comparison_bar_data") or not self.comparison_bar_data:
                QMessageBox.information(self, '提示', "请先生成曲线图以提取最差bit数据")
                return

            bar_data = self.comparison_bar_data
            mark_freqGs = list(bar_data.keys())
            valid_options = list({d['option'] for data in bar_data.values() for d in data})
            num_freqs = len(mark_freqGs)
            num_options = len(valid_options)
            fig, axes = plt.subplots(num_freqs, num_options, figsize=(5 * num_options, 3 * num_freqs), squeeze=False)
            fig_id = self.current_fig_id
            self.current_fig_id += 1
            self.figures[fig_id] = {"fig": fig, "lines": [], "cids": []}
            legend_handles = {}

            for freq_idx, freq in enumerate(mark_freqGs):
                current_data = [d for d in bar_data[freq] if d['option'] in valid_options]
                if not current_data:
                    continue
                file_names = sorted(list(set(d['file'] for d in current_data)))

                for opt_idx, option in enumerate(valid_options):
                    ax = axes[freq_idx][opt_idx]
                    values, freq_at_max_list, colors = [], [], []

                    # 预设一组协调的颜色（可以使用任何你喜欢的颜色组合）
                    bar_colors = ['#1a5276', '#2874a6', '#3498db', '#5dade2',
                                  '#85c1e9', '#aed6f1', '#d4e6f1']

                    for file_idx, file_name in enumerate(file_names):
                        match = [d for d in current_data if d['file'] == file_name and d['option'] == option]
                        if match:
                            values.append(float(match[0]['value']))
                            freq_at_max_list.append(float(match[0]['freq_at_max']))
                            # 使用预设颜色，按文件索引循环使用
                            # colors.append(bar_colors[file_idx % len(bar_colors)])
                            colors.append(match[0]['color'])
                        else:
                            values.append(0.0)
                            freq_at_max_list.append(0.0)
                            colors.append('gray')  # 无数据时使用灰色

                    x_pos = np.arange(len(file_names))
                    bars = ax.bar(x_pos, values, width=0.6, color=colors)

                    for i, val in enumerate(values):
                        if val != 0:
                            ax.text(x_pos[i], val, f'{val:.2f}\n@{freq_at_max_list[i]:.1f}GHz',
                                    ha='center', va='bottom', fontsize=10)

                    if freq_idx == 0:
                        ax.set_title(option_display_name(option))
                    ax.set_ylabel(f"0-{freq}GHz\n最差值 ({option_unit(option)})")

                    ax.set_xticks(x_pos)
                    ax.set_xticklabels([''] * len(file_names))
                    ax.grid(True, axis='y')


                    if freq_idx == 0 and opt_idx == 0:
                        for i, file_name in enumerate(file_names):
                            if file_name not in legend_handles:
                                legend_handles[file_name] = mpatches.Patch(color=colors[i], label=file_name)

            fig.legend(handles=legend_handles.values(), loc='upper right', bbox_to_anchor=(1.02, 1.0))
            fig.tight_layout(rect=[0, 0, 0.96, 1])
            fig.show()

        except Exception as e:
            show_error(self, f"生成横向比较柱状图时出错: {str(e)}")

    def get_worst_bit_data(self, file_name, network, option, port_pairs, mark_freqGs):
        """获取指定文件和分析项目的最差bit数据（以目标频点以下频段内的最差点为准）"""
        try:
            s_params = self._get_s_params(file_name, network)
            freqG = network.frequency.f / 1e9
            num_port = network.nports

            # 处理串扰和指标
            if option in ['FarEnd_XTSum', 'NearEnd_XTSum', "VTF_XTSum"]:
                return self.get_xtsum_worst_data(file_name, network, option, port_pairs, mark_freqGs)

            worst_bit = None
            worst_value = -np.inf if option not in ['insertion_loss', 'VTF_loss'] else np.inf  # 插入损耗越小越差

            # 确定要分析的端口组
            if option in ['insertion_loss', 'VTF_loss']:
                port1_group = port_pairs[1]
                port2_group = port_pairs[0]
                port_group = [port1_group, port2_group]
                plot_mode = "幅度 (dB)"
            elif option == 'return_loss':
                port1_group = port_pairs[0]
                port2_group = port_pairs[0]
                port_group = [port1_group, port2_group]
                plot_mode = "幅度 (dB)"
            elif option == 'FarEnd_signal_crosstalk':
                port1_group = []
                port2_group = []
                for i in range(num_port // 2):
                    p1 = port_pairs[1][i]  # 受害端口
                    for j in range(num_port // 2):
                        p2 = port_pairs[0][j]  # 攻击端口
                        if i != j:
                            port1_group.append(p1)
                            port2_group.append(p2)
                port_group = [port1_group, port2_group]
                plot_mode = "幅度 (dB)"
            elif option == 'NearEnd_signal_crosstalk':
                port1_group = []
                port2_group = []
                for i in range(num_port // 2):
                    p1 = port_pairs[0][i]  # 受害端口
                    for j in range(num_port // 2):
                        p2 = port_pairs[0][j]  # 攻击端口
                        if i != j:
                            port1_group.append(p1)
                            port2_group.append(p2)
                port_group = [port1_group, port2_group]
                plot_mode = "幅度 (dB)"
            else:
                return None  # 不支持的比较选项

            # 找出最差bit
            for p1, p2 in zip(port_group[0], port_group[1]):
                s_param = s_params[:, p1 - 1, p2 - 1]
                if option == 'VTF_loss':
                    z0 = network.z0
                    z_source = z0[:, p2 - 1]
                    z_load = z0[:, p1 - 1]
                    s_param = 0.5 * s_param * np.sqrt(z_load / z_source)  # 这里不再该变量名了，但是实际上是VTF了
                y_data = 20 * np.log10(np.abs(s_param))


                # 计算关注频点内的最差值
                if mark_freqGs:
                    max_values = []
                    freq_at_max = []
                    mark_values = []
                    for freq in mark_freqGs:
                        mask = (freqG <= freq)
                        if option not in ['insertion_loss', 'VTF_loss']:
                            max_val = np.max(y_data[mask])
                            max_idx = np.argmax(y_data[mask])
                        else:
                            max_val = np.min(y_data[mask])
                            max_idx = np.argmin(y_data[mask])
                        freq_idx = np.argmin(np.abs(freqG - freq))
                        max_values.append(max_val)
                        mark_values.append(y_data[freq_idx])
                        freq_at_max.append(freqG[mask][max_idx])

                    if option not in ['insertion_loss', 'VTF_loss']:
                        current_worst = np.max(max_values)
                    else:
                        current_worst = np.min(max_values)
                else:
                    if option not in ['insertion_loss', 'VTF_loss']:
                        current_worst = np.max(y_data)
                    else:
                        current_worst = np.min(y_data)

                # 更新最差bit
                if (option not in ['insertion_loss', 'VTF_loss'] and current_worst > worst_value) or \
                        (option in ['insertion_loss', 'VTF_loss'] and current_worst < worst_value):
                    worst_value = current_worst
                    worst_bit = {
                        'line': p2,
                        'port': f'S{p1},{p2}',
                        'freqG': freqG,
                        'y_data': y_data
                    }

                    # 记录关注频点数据
                    if mark_freqGs:
                        worst_bit['max_values'] = max_values
                        worst_bit['freq_at_max'] = freq_at_max
                        worst_bit['mark_values'] = mark_values

            return worst_bit

        except Exception as e:
            show_error(self, f"获取最差bit数据时出错: {str(e)}")
            return None

    def get_xtsum_worst_data(self, file_name, network, option, port_pairs, mark_freqGs):
        """获取串扰和的最差数据（以目标频点以下频段内的最差点为准）"""
        try:
            s_params = self._get_s_params(file_name, network)
            freqG = network.frequency.f / 1e9
            num_port = network.nports

            # 确定求和模式
            if self.power_radio.isChecked():
                sum_mode = "Power"
            elif self.modulo_radio.isChecked():
                sum_mode = "Amplitude_Modulo"
            elif self.vector_radio.isChecked():
                sum_mode = "Amplitude_Vector"
            else:
                sum_mode = "Power"

            # 确定是远端还是近端
            end_mode = "Far_end" if option in ["FarEnd_XTSum", "VTF_XTSum"] else "Near_end"

            worst_value = -np.inf
            worst_line = None
            worst_data = None
            # print(port_pairs)
            for i in range(num_port // 2):
                # p1 是当前 bit 的接收端（由 end_mode 决定）
                if end_mode == "Far_end":
                    p1 = port_pairs[1][i]
                    other_ports = [port_pairs[0][j] for j in range(num_port // 2) if j != i]
                else:
                    p1 = port_pairs[0][i]
                    other_ports = [port_pairs[0][j] for j in range(num_port // 2) if j != i]

                raw_data = np.zeros(len(s_params), dtype=np.complex128)
                # raw_data = np.zeros(len(s_params))
                for p2 in other_ports:
                    if option == "VTF_XTSum":
                        z0 = network.z0
                        z_source = z0[:, p2 - 1]
                        z_load = z0[:, p1 - 1]
                        vtf_ratio = 0.5 * np.sqrt(z_load / z_source)
                        raw_data += np.abs(vtf_ratio * s_params[:, p1 - 1, p2 - 1]) ** 2
                    else:
                        if sum_mode == "Power":
                            raw_data += np.abs(s_params[:, p1 - 1, p2 - 1]) ** 2
                        elif sum_mode == "Amplitude_Modulo":
                            raw_data += np.abs(s_params[:, p1 - 1, p2 - 1])
                        elif sum_mode == "Amplitude_Vector":
                            raw_data += s_params[:, p1 - 1, p2 - 1]

                if sum_mode == "Power":
                    y_data = 10 * np.log10(np.abs(raw_data))
                else:
                    y_data = 20 * np.log10(np.abs(raw_data))

                # 计算关注频点内的最差值
                if mark_freqGs:
                    max_values = []
                    freq_at_max = []
                    mark_values = []
                    for freq in mark_freqGs:
                        mask = (freqG <= freq)
                        current_max = np.max(y_data[mask])
                        max_idx = np.argmax(y_data[mask])
                        max_values.append(current_max)  # 最大值
                        freq_at_max.append(freqG[mask][max_idx])
                        freq_idx = np.argmin(np.abs(freqG - freq))
                        mark_values.append(y_data[freq_idx])  # mark处值

                    current_worst = np.max(max_values)
                else:
                    current_worst = np.max(y_data)

                if current_worst > worst_value:
                    worst_value = current_worst
                    worst_line = i + 1
                    worst_data = {
                        'line': worst_line,
                        'port': f"port{p1}",
                        'freqG': freqG,
                        'y_data': y_data
                    }
                    if mark_freqGs:
                        worst_data['max_values'] = max_values
                        worst_data['freq_at_max'] = freq_at_max
                        worst_data['mark_values'] = mark_values

            return worst_data

        except Exception as e:
            show_error(self, f"获取串扰和最差数据时出错: {str(e)}")
            return None

    def generate_plots(self):
        # 获取用户选择
        self.s_params_files = self.parent.get_selected_file_keys()
        if not self.s_params_files:
            QMessageBox.warning(self, '错误', '请先选择需要进行频域分析的S参数文件！')
            return
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
                network = self.parent.get_network(file2plot)
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
                    if self.option in ['insertion_loss', 'VTF_loss']:
                        plot_mode = "幅度 (dB)"
                        port1_group = port_pairs[1]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(file2plot, network, port_group, plot_mode, worst_mode="min")
                    elif self.option == 'return_loss':
                        port1_group = port_pairs[0]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(file2plot, network, port_group)
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
                        self.plot_s_curve(file2plot, network, port_group)
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
                        self.plot_s_curve(file2plot, network, port_group)
                    elif self.option == 'group_delay':
                        plot_mode = "群延迟 (fs)"
                        port1_group = port_pairs[1]
                        port2_group = port_pairs[0]
                        port_group = [port1_group, port2_group]
                        self.plot_s_curve(file2plot, network, port_group, plot_mode)
                    elif self.option == 'pn_skew':
                        plot_mode = "PN_skew (fs)"
                        self.plot_pn_mismatch(file2plot, network, port_pairs, plot_mode)
                    elif self.option == 'pn_skew_dev':
                        # 确认公式
                        plot_mode = "PN_skew_dev (fs)"
                        self.plot_pn_mismatch(file2plot, network, port_pairs, plot_mode)
                    elif self.option == 'pn_mag_mismatch':
                        plot_mode = "PN_Magnitude_Mismatch (dB)"
                        self.plot_pn_mismatch(file2plot, network, port_pairs, plot_mode)
                    elif self.option in ["FarEnd_XTSum", "VTF_XTSum"]:
                        end_mode = "Far_end"
                        self.plot_s_xtsum(file2plot, network, port_pairs, end_mode)
                    elif self.option == 'NearEnd_XTSum':
                        end_mode = "Near_end"
                        self.plot_s_xtsum(file2plot, network, port_pairs, end_mode)

                self.all_results[file2plot] = self.file_result
            except:
                show_error(self, "绘制曲线时出错")

        self.print_results()
        print("✅ Figures plot and Tables print finished")

    def plot_s_curve(self, file_name, network, port_group, plot_mode="幅度 (dB)", worst_mode="max"):
        fig, ax = plt.subplots()
        fig_id = self.current_fig_id
        self.current_fig_id += 1
        self.current_figure = fig  # ✅ 避免后续找不到图形

        self.figures[fig_id] = {
            "fig": fig,
            "lines": [],
            "cids": []
        }

        s_params = self._get_s_params(file_name, network)
        freqG = network.frequency.f / 1e9
        input = self.freG_input.text()
        mark_freqGs = parse_port_input(input, type="freq")
        print(mark_freqGs)

        ax.set_title(network.name)
        self.mode_result = []

        for p1, p2 in zip(port_group[0], port_group[1]):
            if self.option == 'VTF_loss':
                z0 = network.z0
                z_source = z0[:, p2 - 1]
                z_load = z0[:, p1 - 1]
                vtf_ratio = 0.5 * np.sqrt(z_load / z_source)
                s_param = s_params[:, p1 - 1, p2 - 1]*vtf_ratio
            else:
                s_param = s_params[:, p1 - 1, p2 - 1]

            if plot_mode == "幅度 (dB)":
                y_data = 20 * np.log10(np.abs(s_param))
            else:
                phase = np.unwrap(np.angle(s_param))
                tau_g = -np.gradient(phase, freqG * 1e9) / (2 * np.pi)
                y_data = tau_g * 1e15  # fs

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
        ax.set_ylabel(option_axis_label(self.option))
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

    def plot_pn_mismatch(self, file_name, network, port_pairs, plot_mode):
        s_params = self._get_s_params(file_name, network)
        num_port = network.nports
        if num_port % 4 != 0:
            QMessageBox.warning(self, '端口错误', '端口数非4的倍数，请确认是否为差分线的单端S参数')
            return

        input = self.freG_input.text()
        mark_freqGs = parse_port_input(input, type="freq")

        plt.rcParams['axes.unicode_minus'] = False

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
            freq = network.frequency.f
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
                y_data = abs(raw_data1 - raw_data2)/(2*np.pi*freqG) * 1e6
                # y_data = abs(raw_data1 - raw_data2) * 180 / freqG / 2 * 1e3
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

    def plot_s_xtsum(self, file_name, network, port_pairs, end_mode):
        if self.power_radio.isChecked():
            sum_mode = "Power"
        elif self.modulo_radio.isChecked():
            sum_mode = "Amplitude_Modulo"
        elif self.vector_radio.isChecked():
            sum_mode = "Amplitude_Vector"

        freqG = network.frequency.f / 1e9
        s_params = self._get_s_params(file_name, network)
        num_port = network.nports
        input = self.freG_input.text()
        mark_freqGs = parse_port_input(input, type="freq")


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
            raw_data = np.zeros(len(s_params), dtype=np.complex128)  # 关键修改：指定复数类型
            for j in range(num_port // 2):
                p2 = port_pairs[0][j]
                if i != j:
                    if self.option == "VTF_XTSum":
                        z0 = network.z0
                        z_source = z0[:, p2 - 1]
                        z_load = z0[:, p1 - 1]
                        vtf_ratio = 0.5 * np.sqrt(z_load / z_source)
                        raw_data += np.abs(vtf_ratio * s_params[:, p1 - 1, p2 - 1]) ** 2
                    else:
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
            label = f'Line{i + 1}(Port{p1}): {data_string}'
            line, = ax.plot(freqG, y_data, label=label, picker=5)
            self.figures[fig_id]["lines"].append(line)

            for x_line in mark_freqGs:
                ax.axvline(x=x_line, linestyle=':', alpha=1)

            port_result = {'port': f'Line{i + 1}(Port{p1})', 'mark_info': mark_info, 'max_info': worst_info}
            self.mode_result.append(port_result)

        ax.set_title(network.name)
        ax.set_xlabel("frequency (GHz)")
        ax.set_ylabel(option_axis_label(self.option))
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
            self.s_params_files = self.parent.get_selected_file_keys()
            if not self.s_params_files:
                QMessageBox.warning(self, '错误', '请先选择需要进行频域分析的S参数文件！')
                return
            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            input = self.freG_input.text()
            mark_freqGs = parse_port_input(input, type="freq")
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

    def print_comparison_results(self, mode="specific"):
        """从all_results中提取并打印结果，兼容两种模式"""
        try:
            # 获取当前选项和指定线号
            selected_options = [k for k, cb in self.analysis_checks.items() if cb.isChecked()]
            specified_lines = [int(x.strip()) for x in self.line_input.text().split(',') if x.strip()]
            input = self.freG_input.text()
            mark_freqGs = parse_port_input(input, type="freq")

            if not self.all_results or not isinstance(self.all_results, dict):
                print("⚠️ 没有可打印的结果数据")
                return

            # 遍历所有选中的分析选项
            for option in selected_options:
                if not isinstance(option, str) or option not in self.all_results:
                    continue

                if mode == "specific":
                    print(f"\n🔍 分析模式: {option} - 线号 {','.join(map(str, specified_lines))}")
                else:
                    print(f"\n🔍 分析模式: {option} - 最差bit")
                print("═" * 50)

                # 遍历当前option下的所有文件
                for file_path, results in self.all_results[option].items():
                    file_name = os.path.basename(file_path)
                    print(f"\n📄 文件: {file_name}")
                    print("-" * 60)

                    # 创建数据表格
                    table_data = []
                    for result in results:
                        # 处理可能的结果列表（兼容两种模式）
                        result_list = []
                        if isinstance(result, list):
                            result_list.extend(result)  # 串扰模式的多结果
                        elif mode == "comparison":
                            result_list.append(result)  # 比较模式的单结果
                        elif 'line_num' in result and result['line_num'] in specified_lines:
                            result_list.append(result)  # 特定线号模式的单结果

                        for single_result in result_list:
                            # 跳过没有line_num的结果（比较模式可能没有）
                            # if mode != "comparison" and 'line_num' not in single_result:
                            #     continue

                            # row = {
                            #     '线号': single_result.get('line_num', '最差') if mode != "comparison" else '最差',
                            #     '端口': self._format_port_info(single_result.get('port'))
                            # }
                            row = {
                                '线号': single_result.get('line_num'),
                                '端口': self._format_port_info(single_result.get('port'))
                            }

                            # 添加频点数据（兼容两种数据结构）
                            mark_info = single_result.get('mark_info', [])
                            max_info = single_result.get('max_info', [])

                            # 统一处理为列表形式
                            mark_list = mark_info if isinstance(mark_info, list) else [mark_info]
                            max_list = max_info if isinstance(max_info, list) else [max_info]

                            for freq_idx, freq in enumerate(mark_freqGs):
                                if freq_idx < len(mark_list) and freq_idx < len(max_list):
                                    mark = mark_list[freq_idx] if isinstance(mark_list[freq_idx], dict) else {
                                        'value': mark_list[freq_idx]}
                                    max_val = max_list[freq_idx] if isinstance(max_list[freq_idx], dict) else {
                                        'freq': 0, 'value': max_list[freq_idx]}

                                    row.update({
                                        f'{freq}GHz处数值': round(mark.get('value', 0), 3),
                                        f'最差值频点': round(max_val.get('freq', 0), 3),
                                        f'最差值': round(max_val.get('value', 0), 3)
                                    })
                            table_data.append(row)

                    # 打印表格
                    if table_data:
                        df = pd.DataFrame(table_data)
                        print(df.to_string(index=False))

        except Exception as e:
            show_error(self, f"打印结果时出错: {str(e)}")

    def _format_port_info(self, port):
        """Helper to format port information consistently"""
        if isinstance(port, str):
            return port
        elif len(port) == 4:  # Differential pair
            return f"S({port[0]},{port[1]}),({port[2]},{port[3]})"
        elif len(port) == 2:  # Single-ended
            return f"S{port[0]},{port[1]}"
        return str(port)

    def _format_port_info(self, port):
        """Helper to format port information consistently"""
        if isinstance(port, str):
            return port
        elif len(port) == 4:  # Differential pair
            return f"S({port[0]},{port[1]}),({port[2]},{port[3]})"
        elif len(port) == 2:  # Single-ended
            return f"S{port[0]},{port[1]}"
        return str(port)

    def _print_specific_mode_data(self, mode_result, mark_freqGs):
        """处理指定线号模式的数据打印"""
        for line_data in mode_result:
            # 提取线号信息
            line_info = f"线{line_data.get('line_num', 'N/A')}"
            port_info = str(line_data.get('port', 'N/A'))

            print(f"\n{line_info} {port_info}")

            # 打印频点数据
            for freq_idx, freq in enumerate(mark_freqGs):
                row = [
                    f"{freq}GHz",
                    round(line_data['mark_info'][freq_idx].get('value', 0), 3),
                    round(line_data['max_info'][freq_idx].get('freq', 0), 3),
                    round(line_data['max_info'][freq_idx].get('value', 0), 3)
                ]
                print(f"  {row[0]}: 值={row[1]} @ {row[2]}GHz (最差={row[3]})")

    def _print_comparison_mode_data(self, mode_result, mark_freqGs):
        """处理最差曲线模式的数据打印"""
        # 最差曲线模式下，mode_result已经是经过筛选的最差数据
        port_info = str(mode_result.get('port', 'N/A'))
        print(f"\n最差端口: {port_info}")

        for freq_idx, freq in enumerate(mark_freqGs):
            row = [
                f"{freq}GHz",
                round(mode_result['mark_info'][freq_idx].get('value', 0), 3),
                round(mode_result['max_info'][freq_idx].get('freq', 0), 3),
                round(mode_result['max_info'][freq_idx].get('value', 0), 3)
            ]
            print(f"  {row[0]}: 值={row[1]} @ {row[2]}GHz (最差={row[3]})")

    def _print_plot_mode_data(self, mode_result, mark_freqGs):
        """处理原始单文件模式的数据打印"""
        for item in mode_result:
            port_info = str(item.get('port', 'N/A'))
            print(f"\n端口: {port_info}")

            for freq_idx, freq in enumerate(mark_freqGs):
                row = [
                    f"{freq}GHz",
                    round(item['mark_info'][freq_idx].get('value', 0), 3),
                    round(item['max_info'][freq_idx].get('freq', 0), 3),
                    round(item['max_info'][freq_idx].get('value', 0), 3)
                ]
                print(f"  {row[0]}: 值={row[1]} @ {row[2]}GHz (最差={row[3]})")

    def excel_export(self):
        """
        导出Excel（优化布局+交互式保存）
        """

        def sanitize_sheet_name(name):
            """清理非法字符，替换为下划线"""
            return re.sub(r'[\\/*?:[\]]', '_', name)

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

        # 检查是否有分析结果
        if not hasattr(self, 'all_results') or not self.all_results:
            QMessageBox.warning(self, "警告", "请先执行【按文件绘制】")
            return
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
            input = self.freG_input.text()
            mark_freqGs = parse_port_input(input, type="freq")
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
