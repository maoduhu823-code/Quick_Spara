# UI2_SE2Diff.py
# 界面调试未完成/端口命名有bug
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QRadioButton,
                             QGroupBox, QButtonGroup, QFrame)
from PyQt6.QtGui import QPixmap
from Basic_function_module import *


class DiffConversionDialog(QDialog):
    def __init__(self, n_ports, parent=None):
        super().__init__(parent)
        self.setWindowTitle("差分参数转换设置")
        self.setGeometry(200, 100, 350, 800)
        self.setFixedSize(350, 800)  # 固定窗口大小
        self.setup_ui()


    def setup_ui(self):
        layout = QVBoxLayout()

        # ====== 逻辑视角选择 ======
        logic_group = QGroupBox("选择逻辑视角")
        logic_group.setFixedHeight(70)  # 固定高度
        logic_layout = QHBoxLayout()

        self.logic_button_group = QButtonGroup(self)

        # 线逻辑单选按钮
        self.line_logic_radio = QRadioButton("线逻辑")
        self.line_logic_radio.setChecked(True)
        self.logic_button_group.addButton(self.line_logic_radio)
        logic_layout.addWidget(self.line_logic_radio)

        # 端口逻辑单选按钮
        self.port_logic_radio = QRadioButton("端口逻辑")
        self.logic_button_group.addButton(self.port_logic_radio)
        logic_layout.addWidget(self.port_logic_radio)

        logic_group.setLayout(logic_layout)
        layout.addWidget(logic_group)

        # ====== 动态内容容器 ======
        self.content_stack = QFrame()
        content_layout = QVBoxLayout()

        # ====== 线逻辑部分 ======
        self.line_content = QFrame()
        line_layout = QVBoxLayout()

        # 端口排列方式
        port_group = QGroupBox("端口排列方式")
        port_layout = QVBoxLayout()

        self.inside_radio = QRadioButton("端口序号按侧分布")
        port_layout.addWidget(self.inside_radio)
        inside_img = QLabel()
        inside_img.setPixmap(QPixmap(resource_path("resources/Port_inside.PNG")))
        inside_img.setScaledContents(True)
        port_layout.addWidget(inside_img)

        self.inline_radio = QRadioButton("端口序号按线分布")
        port_layout.addWidget(self.inline_radio)
        inline_img = QLabel()
        inline_img.setPixmap(QPixmap(resource_path("resources/Port_inline.PNG")))
        inline_img.setScaledContents(True)
        port_layout.addWidget(inline_img)

        port_group.setLayout(port_layout)
        line_layout.addWidget(port_group)

        # 阻抗设置
        self.line_impedance_group = QGroupBox("阻抗设置(Z_comm=Z_diff/4)")
        impedance_layout = QHBoxLayout()
        impedance_layout.addWidget(QLabel("Z_diff(左)："))
        self.Diff_impedance_left = QLineEdit("90")
        impedance_layout.addWidget(self.Diff_impedance_left)
        impedance_layout.addWidget(QLabel("Z_diff(右)："))
        self.Diff_impedance_right = QLineEdit("90")
        impedance_layout.addWidget(self.Diff_impedance_right)
        self.line_impedance_group.setLayout(impedance_layout)
        line_layout.addWidget(self.line_impedance_group)

        # 部分差分模式
        partial_diff_group = QGroupBox("部分差分模式")
        partial_diff_layout = QVBoxLayout()

        self.partial_diff_radio = QRadioButton("启用部分差分")
        partial_diff_layout.addWidget(self.partial_diff_radio)

        self.diff_lines_edit = QLineEdit()
        self.diff_lines_edit.setPlaceholderText("例如: 1 2 或 3:5")
        self.diff_lines_edit.setEnabled(False)
        partial_diff_layout.addWidget(self.diff_lines_edit)

        hint_label = QLabel("输入需要转换的差分【线】\n（如'1 2'表示line1和line2)")
        hint_label.setWordWrap(True)
        partial_diff_layout.addWidget(hint_label)

        partial_diff_group.setLayout(partial_diff_layout)
        line_layout.addWidget(partial_diff_group)

        self.line_content.setLayout(line_layout)
        content_layout.addWidget(self.line_content)

        # ====== 端口逻辑部分 ======
        self.port_content = QFrame()
        self.port_content.setVisible(False)  # 默认隐藏
        port_view_layout = QVBoxLayout()

        # 自定义端口映射
        custom_group = QGroupBox("自定义端口映射")
        custom_layout = QVBoxLayout()

        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("请用空格隔开端口序号，如：1 3 2 4")
        custom_layout.addWidget(self.custom_input)

        custom_layout.addWidget(QLabel("输入格式说明：\n"
                                       "• 按顺序输入端口号，程序将按顺序配对\n"
                                       "• 例如输入：1 3 2 4 5 7 6 8\n"
                                       "• 将生成4个差分端口对：[1,3], [2,4], [5,7], [6,8]"))
        custom_layout.addStretch()
        custom_group.setLayout(custom_layout)
        port_view_layout.addWidget(custom_group)

        # 端口逻辑下的阻抗设置
        self.port_impedance_group = QGroupBox("阻抗设置(Z_comm=Z_diff/4)")
        port_impedance_layout = QHBoxLayout()
        port_impedance_layout.addWidget(QLabel("Z_diff："))  # 去掉"左/右"标识
        self.port_Diff_impedance = QLineEdit("100")  # 改为单个输入框
        port_impedance_layout.addWidget(self.port_Diff_impedance)
        self.port_impedance_group.setLayout(port_impedance_layout)
        port_view_layout.addWidget(self.port_impedance_group)

        self.port_content.setLayout(port_view_layout)
        content_layout.addWidget(self.port_content)

        # ====== 输出模式选择 ======
        self.output_group = QGroupBox("输出模式")
        self.output_group.setFixedHeight(100)  # 固定高度
        output_layout = QVBoxLayout()

        self.sdd_only_radio = QRadioButton("仅差分参数 (SDD)")
        self.full_mixed_radio = QRadioButton("完整混合模式参数 (SDD+SCD+SDC+SCC)")

        output_layout.addWidget(self.sdd_only_radio)
        output_layout.addWidget(self.full_mixed_radio)
        self.output_group.setLayout(output_layout)
        content_layout.addWidget(self.output_group)

        self.content_stack.setLayout(content_layout)
        layout.addWidget(self.content_stack)

        # ====== 信号连接 ======
        self.partial_diff_radio.toggled.connect(self.diff_lines_edit.setEnabled)
        self.line_logic_radio.toggled.connect(self.toggle_logic_view)
        self.port_logic_radio.toggled.connect(self.toggle_logic_view)

        # ====== 默认设置 ======
        self.inside_radio.setChecked(True)
        self.sdd_only_radio.setChecked(True)

        # 确认按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def toggle_logic_view(self):
        """切换显示对应的逻辑设置内容"""
        show_line = self.line_logic_radio.isChecked()
        self.line_content.setVisible(show_line)
        self.port_content.setVisible(not show_line)

        # 动态调整窗口大小
        # self.adjustSize()

    def get_conversion_params(self):
        """获取差分转换参数"""
        try:
            is_line_logic = self.line_logic_radio.isChecked()

            params = {
                'z0_diff': [float(self.Diff_impedance_left.text()),
                            float(self.Diff_impedance_right.text())] if is_line_logic
                else float(self.port_Diff_impedance.text()),  # 端口模式返回单值

                'output_mode': 'sdd_only' if self.sdd_only_radio.isChecked() else 'full',
                'Logic': 'line' if is_line_logic else 'port'
            }

            if is_line_logic:
                params.update({
                    'port_mode': 'inside' if self.inside_radio.isChecked() else 'inline',
                    'diff_list': parse_port_input(self.diff_lines_edit.text())
                    if self.partial_diff_radio.isChecked() else []
                })
            else:
                params.update({
                    'port_mode': 'inport',
                    'diff_list': list(map(int, self.custom_input.text().split()))
                })

            if params['diff_list'] and len(params['diff_list']) % 2 != 0:
                raise ValueError("端口/线对数量必须是偶数")

            return params

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return None
        except Exception as e:
            show_error(self, f"参数获取错误: {str(e)}")
            return None