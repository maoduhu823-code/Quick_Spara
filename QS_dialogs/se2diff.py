from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QRadioButton,
                             QGroupBox, QButtonGroup, QFrame, QMessageBox,
                             QSizePolicy)
from PyQt6.QtGui import QPixmap

from app_utils import resource_path, show_error
from sparam_core import parse_port_input


class DiffConversionDialog(QDialog):
    def __init__(self, n_ports, parent=None):
        super().__init__(parent)
        self.setWindowTitle("差分参数转换设置")
        self.setFixedSize(560, 480)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # ── 逻辑视角切换 ──
        logic_group = QGroupBox("选择逻辑视角")
        logic_layout = QHBoxLayout()
        self.logic_button_group = QButtonGroup(self)
        self.line_logic_radio = QRadioButton("线逻辑")
        self.line_logic_radio.setChecked(True)
        self.logic_button_group.addButton(self.line_logic_radio)
        logic_layout.addWidget(self.line_logic_radio)
        self.port_logic_radio = QRadioButton("端口逻辑")
        self.logic_button_group.addButton(self.port_logic_radio)
        logic_layout.addWidget(self.port_logic_radio)
        logic_layout.addStretch()
        logic_group.setLayout(logic_layout)
        layout.addWidget(logic_group)

        self.content_stack = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # ══════════════ 线逻辑面板 ══════════════
        self.line_content = QFrame()
        line_layout = QVBoxLayout()
        line_layout.setSpacing(6)
        line_layout.setContentsMargins(0, 0, 0, 0)

        # 端口排列方式 — 左右并排
        port_group = QGroupBox("端口排列方式")
        port_layout = QHBoxLayout()
        port_layout.setSpacing(8)

        self.port_mode_group = QButtonGroup(self)

        for radio_attr, label, img_key in [
            ('inside_radio', '端口序号按侧分布', 'Port_inside.PNG'),
            ('inline_radio', '端口序号按线分布', 'Port_inline.PNG'),
        ]:
            cell = QFrame()
            cell_layout = QVBoxLayout()
            cell_layout.setSpacing(4)
            radio = QRadioButton(label)
            setattr(self, radio_attr, radio)
            self.port_mode_group.addButton(radio)
            cell_layout.addWidget(radio)

            img_label = QLabel()
            px = QPixmap(resource_path(f"resources/{img_key}"))
            img_label.setPixmap(px if not px.isNull() else QPixmap())
            img_label.setScaledContents(True)
            img_label.setFixedHeight(110)
            img_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cell_layout.addWidget(img_label)

            cell.setLayout(cell_layout)
            port_layout.addWidget(cell)

        port_group.setLayout(port_layout)
        line_layout.addWidget(port_group)

        # 阻抗设置
        self.line_impedance_group = QGroupBox("阻抗设置 (Z_comm = Z_diff / 4)")
        impedance_layout = QHBoxLayout()
        impedance_layout.addWidget(QLabel("Z_diff (左)："))
        self.Diff_impedance_left = QLineEdit("90")
        self.Diff_impedance_left.setFixedWidth(60)
        impedance_layout.addWidget(self.Diff_impedance_left)
        impedance_layout.addSpacing(16)
        impedance_layout.addWidget(QLabel("Z_diff (右)："))
        self.Diff_impedance_right = QLineEdit("90")
        self.Diff_impedance_right.setFixedWidth(60)
        impedance_layout.addWidget(self.Diff_impedance_right)
        impedance_layout.addStretch()
        self.line_impedance_group.setLayout(impedance_layout)
        line_layout.addWidget(self.line_impedance_group)

        # 部分差分模式 — radio + 输入框同行
        partial_diff_group = QGroupBox("部分差分模式")
        partial_diff_layout = QVBoxLayout()
        partial_diff_layout.setSpacing(4)

        partial_top = QHBoxLayout()
        self.partial_diff_radio = QRadioButton("启用部分差分")
        partial_top.addWidget(self.partial_diff_radio)
        self.diff_lines_edit = QLineEdit()
        self.diff_lines_edit.setPlaceholderText("例如: 1 2 或 3:5")
        self.diff_lines_edit.setEnabled(False)
        partial_top.addWidget(self.diff_lines_edit)
        partial_diff_layout.addLayout(partial_top)

        hint_label = QLabel("输入需要转换的差分【线】（如 '1 2' 表示 line1 和 line2）")
        hint_label.setWordWrap(True)
        partial_diff_layout.addWidget(hint_label)
        partial_diff_group.setLayout(partial_diff_layout)
        line_layout.addWidget(partial_diff_group)

        self.line_content.setLayout(line_layout)
        content_layout.addWidget(self.line_content)

        # ══════════════ 端口逻辑面板 ══════════════
        self.port_content = QFrame()
        self.port_content.setVisible(False)
        port_view_layout = QVBoxLayout()
        port_view_layout.setSpacing(6)
        port_view_layout.setContentsMargins(0, 0, 0, 0)

        custom_group = QGroupBox("自定义端口映射")
        custom_layout = QVBoxLayout()
        custom_layout.setSpacing(4)
        self.custom_input = QLineEdit()
        self.custom_input.setPlaceholderText("请用空格隔开端口序号，如：1 3 2 4")
        custom_layout.addWidget(self.custom_input)
        custom_layout.addWidget(QLabel(
            "按顺序输入端口号，程序将按顺序两两配对\n"
            "例如输入 1 3 2 4 5 7 6 8 → 生成 4 对：[1,3] [2,4] [5,7] [6,8]"
        ))
        custom_group.setLayout(custom_layout)
        port_view_layout.addWidget(custom_group)

        self.port_impedance_group = QGroupBox("阻抗设置 (Z_comm = Z_diff / 4)")
        port_impedance_layout = QHBoxLayout()
        port_impedance_layout.addWidget(QLabel("Z_diff："))
        self.port_Diff_impedance = QLineEdit("100")
        self.port_Diff_impedance.setFixedWidth(60)
        port_impedance_layout.addWidget(self.port_Diff_impedance)
        port_impedance_layout.addStretch()
        self.port_impedance_group.setLayout(port_impedance_layout)
        port_view_layout.addWidget(self.port_impedance_group)
        port_view_layout.addStretch()

        self.port_content.setLayout(port_view_layout)
        content_layout.addWidget(self.port_content)

        # ── 输出模式（两个面板共用） ──
        self.output_group = QGroupBox("输出模式")
        output_layout = QHBoxLayout()
        output_button_group = QButtonGroup(self)
        self.sdd_only_radio = QRadioButton("仅差分参数 (SDD)")
        self.full_mixed_radio = QRadioButton("完整混合模式参数 (SDD + SCD + SDC + SCC)")
        output_button_group.addButton(self.sdd_only_radio)
        output_button_group.addButton(self.full_mixed_radio)
        output_layout.addWidget(self.sdd_only_radio)
        output_layout.addWidget(self.full_mixed_radio)
        output_layout.addStretch()
        self.output_group.setLayout(output_layout)
        content_layout.addWidget(self.output_group)

        self.content_stack.setLayout(content_layout)
        layout.addWidget(self.content_stack)

        # ── 信号连接 ──
        self.partial_diff_radio.toggled.connect(self.diff_lines_edit.setEnabled)
        self.line_logic_radio.toggled.connect(self.toggle_logic_view)
        self.port_logic_radio.toggled.connect(self.toggle_logic_view)

        self.inside_radio.setChecked(True)
        self.sdd_only_radio.setChecked(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def toggle_logic_view(self):
        show_line = self.line_logic_radio.isChecked()
        self.line_content.setVisible(show_line)
        self.port_content.setVisible(not show_line)

    def get_conversion_params(self):
        try:
            is_line_logic = self.line_logic_radio.isChecked()
            params = {
                'z0_diff': [float(self.Diff_impedance_left.text()),
                            float(self.Diff_impedance_right.text())] if is_line_logic
                else float(self.port_Diff_impedance.text()),
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
