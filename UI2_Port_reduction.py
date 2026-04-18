import sys
import numpy as np
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QCheckBox, QMessageBox, QApplication)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from Basic_function_module import *


class PortReductionDialog(QDialog):
    def __init__(self, parent=None, selected_sparams=None):
        super().__init__(parent)
        self.setWindowTitle("端口阻抗设置")
        self.resize(800, 500)
        self.setMinimumSize(QSize(600, 400))
        self.parent = parent
        self.selected_sparams = selected_sparams or []
        # 存储返回结果
        self.result_data = None

        # 主窗口部件
        self.central_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)

        # 主布局
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # 创建表格
        self.create_table()

        # 按钮区域
        self.button_layout = QHBoxLayout()

        # 添加按钮
        self.add_button = QPushButton("➕ 添加端口组(行)")
        self.add_button.setFixedHeight(40)
        self.add_button.clicked.connect(self.add_port_row)
        self.delete_button = QPushButton("🗑️ 删除端口组(行)")
        self.delete_button.setFixedHeight(40)
        self.delete_button.clicked.connect(self.delete_selected_rows)
        self.set_port = QPushButton("选择端口名")
        self.set_port.setFixedHeight(40)
        self.set_port.clicked.connect(self.fill_by_name_selected)
        self.set_side_button = QPushButton("按侧排布")
        self.set_side_button.setFixedHeight(40)
        self.set_side_button.clicked.connect(self.arrange_by_side)
        self.set_line_button = QPushButton("按线排布")
        self.set_line_button.setFixedHeight(40)
        self.set_line_button.clicked.connect(self.arrange_by_line)
        self.generate_button = QPushButton("生成S参数")
        self.generate_button.setFixedHeight(40)
        self.generate_button.clicked.connect(self.generate_impedance_config)


        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.set_port)
        self.button_layout.addWidget(self.set_side_button)
        self.button_layout.addWidget(self.set_line_button)
        self.button_layout.addWidget(self.generate_button)

        self.main_layout.addLayout(self.button_layout)

        # 初始添加1行
        for i in range(1):
            self.add_port_row(port_num=i + 1)

    def create_table(self):
        """创建并配置表格控件"""
        self.table = QTableWidget()
        self.table.setColumnCount(4)  # 增加一列
        self.table.setHorizontalHeaderLabels(["端口序号", "端接阻抗 (Ω)", "端接电容 (pF)", "是否简并"])

        # 设置列宽策略
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # 第一列可交互调整
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 第二列适应内容
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 新增电容列
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 原第三列后移

        # 设置初始列宽
        self.table.setColumnWidth(0, 350)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)

        # 设置表格属性
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        self.table.setFont(font)

        self.main_layout.addWidget(self.table)

    def delete_selected_rows(self):
        """删除选中的行"""
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return

        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def add_port_row(self, port_num=None, enabled=False):
        """添加一行端口设置（支持多端口输入）"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 端口序号（支持多端口输入）
        port_item = QTableWidgetItem()
        if port_num is not None:
            port_item.setText(str(port_num))
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, port_item)

        # 端接阻抗
        impedance_item = QTableWidgetItem('50')  # 默认50欧姆
        impedance_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, impedance_item)

        # 端接电容 (pF)
        cap_item = QTableWidgetItem('0')  # 默认0pF
        cap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, cap_item)

        # 是否启用复选框
        checkbox = QCheckBox()
        checkbox.setChecked(enabled)
        checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        self.table.setCellWidget(row, 3, widget)  # 改为第4列
        self.table.scrollToBottom()

    def fill_by_name_selected(self):
        """在选中的单元格中填充选中的端口序号"""
        try:
            # 获取所有选中单元格的行列索引
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                QMessageBox.information(self.parent, "提示", "请选择需要填入端口的行")
                return

            for index in selected_indexes:
                row = index.row()
                print(row)
                # 跳过无效行
                if row >= self.table.rowCount():
                    continue

            sparam_file = self.selected_sparams
            selected_ports = check_and_set_port_names(self.parent, sparam_file)
            text_str = " ".join(map(str, selected_ports))
            self.table.item(row, 0).setText(text_str)

        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def arrange_by_side(self):
        """按侧排布端口（假设2n个端口）"""
        try:
            network = get_network(self.parent, self.selected_sparams[0])
            n_ports = network.nports

            if n_ports % 2 != 0:
                QMessageBox.warning(self, "警告", "端口数必须是偶数")
                return

            n = n_ports // 2

            # 清空现有表格
            self.table.setRowCount(0)

            # 添加第一行：1到n
            self.add_port_row(port_num=f"1:{n}")
            # 添加第二行：n+1到2n
            self.add_port_row(port_num=f"{n+1}:{n*2}")

        except Exception as e:
            show_error(self, f"按侧排布时出错: {str(e)}")

    def arrange_by_line(self):
        """按线排布端口（假设2n个端口）"""
        try:
            network = get_network(self.parent, self.selected_sparams[0])
            n_ports = network.nports

            if n_ports % 2 != 0:
                QMessageBox.warning(self, "警告", "端口数必须是偶数")
                return

            n = n_ports // 2

            # 清空现有表格
            self.table.setRowCount(0)
            # 添加第一行：1到n
            self.add_port_row(port_num=f"1:2:{n_ports - 1}")
            # 添加第二行：n+1到2n
            self.add_port_row(port_num=f"2:2:{n_ports}")


        except Exception as e:
            show_error(self, f"按线排布时出错: {str(e)}")

    def generate_impedance_config(self):
        """生成完整的阻抗配置（支持多端口输入）"""
        if not validate_inputs(self):
            return

        try:
            self.port_configs = []
            self.z0_configs = []  # 存储R和C的元组
            self.disabled_ports = []

            for row in range(self.table.rowCount()):
                # 解析多端口
                ports = parse_port_input(self.table.item(row, 0).text())
                resistance = float(self.table.item(row, 1).text())
                capacitance = float(self.table.item(row, 2).text()) * 1e-12  # 转换为法拉
                checkbox = self.table.cellWidget(row, 3).findChild(QCheckBox)  # 改为第4列
                Flag_subnetwork = checkbox.isChecked()

                self.port_configs.append(ports)
                self.z0_configs.append((resistance, capacitance))  # 存储R和C

                if Flag_subnetwork:
                    for port in ports:
                        self.disabled_ports.append(port)

            if not self.port_configs:
                QMessageBox.warning(self, "错误", "没有可用的端口设置")
                return

            # 接受对话框并关闭
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成配置时出错:\n{str(e)}")

    def get_result(self):
        """获取结果数据"""
        return self.port_configs, self.z0_configs, self.disabled_ports

    def compute_load_impedance(self, freq, z_rc):
        """
        计算单个RC配置的负载阻抗向量
        Args:
            freq: 频率数组 (Hz)
            z_rc: 元组 (R, C)，电阻(Ω)和电容(F)
        Returns:
            Z_load: (n_freq,) 的阻抗向量
        """
        R, C = z_rc
        omega = 2 * np.pi * freq
        if C == 0:  # 纯电阻
            return np.full_like(freq, R, dtype=complex)
        else:  # RC并联
            return R / (1 + 1j * omega * R * C)

if __name__ == "__main__":
    # 测试代码
    app = QApplication(sys.argv)
    dialog = PortReductionDialog()

    if dialog.exec() == QDialog.DialogCode.Accepted:
        port_configs, z0_configs, disabled_ports = dialog.get_result()
        network = rf.Network('E:/工作/研究方法调研/S参数后处理/电压传递函数/1650UV100_SUB_20250123_u2s_stx0_HFSSModel1.s44p')
        freq = network.frequency.f  # 获取频率点(Hz)
        z0_new = network.z0.copy()
        print("端口配置:", port_configs)
        print("阻抗配置(R,C):", z0_configs)
        print("简并端口:", disabled_ports)

        # 测试阻抗计算
        for ports, z_rc in zip(port_configs, z0_configs):
            port_indices = [p - 1 for p in ports]
            Z_load = dialog.compute_load_impedance(freq, z_rc)
            for p in port_indices:
                z0_new[:, p] = Z_load

        # 执行重归一化
        network.renormalize(z0_new)
        # print(network.z0)
        input_port = 0  # 假设端口1是输入
        output_port = 22  # 假设端口3是输出(S31)

        # 获取源阻抗和负载阻抗
        Z_source = z0_new[:, input_port]
        Z_load = z0_new[:, output_port]

        # 计算电压传递函数 Vout/Vin
        S = network.s
        S21 = S[:, output_port, input_port]  # S参数
        VTF = 0.5 * S21 * np.sqrt(Z_load / Z_source)  # 电压传递函数公式

        # 打印结果
        print("\nS31端口电压传递函数(VTF):")
        print(f"{'Frequency(GHz)':<15} {'|VTF|':<15} {'Phase(deg)':<15}")
        for f, v in zip(freq / 1e9, VTF):
            print(f"{f:<15.3f} {np.abs(v):<15.6f} {np.angle(v, deg=True):<15.3f}")

        # 绘制幅频和相频特性
        plt.figure(figsize=(12, 6))

        plt.subplot(2, 1, 1)
        plt.plot(freq / 1e9, 20 * np.log10(np.abs(VTF)))
        plt.title('Voltage Transfer Function (S31) - Magnitude')
        plt.ylabel('Magnitude (dB)')
        plt.grid(True)

        plt.subplot(2, 1, 2)
        plt.plot(freq / 1e9, np.angle(VTF, deg=True))
        plt.title('Voltage Transfer Function (S31) - Phase')
        plt.ylabel('Phase (deg)')
        plt.xlabel('Frequency (GHz)')
        plt.grid(True)

        plt.tight_layout()
        plt.show()

    sys.exit(app.exec())
