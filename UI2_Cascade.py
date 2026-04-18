import sys
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QComboBox, QGroupBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor
import random
from Basic_function_module import *

class SParamCascadeDialog(QDialog):
    def __init__(self, parent=None, selected_sparams=None):
        super().__init__(parent)
        self.setWindowTitle("S参数级联设置")
        self.resize(1200, 500)
        self.setMinimumSize(QSize(600, 400))
        self.parent = parent
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # 关闭时销毁对象
        self.setModal(True)  # 设置为模态对话框

        # 存储返回结果
        self.cascade_configs = []

        # 选中的S参数文件列表
        self.selected_sparams = selected_sparams or []

        # 主窗口部件
        self.central_widget = QWidget()
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.central_widget)

        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # 新增操作按钮组
        self.create_operation_buttons()

        self.create_table()
        self.create_action_buttons()
        self.auto_generate_rows()

    def create_operation_buttons(self):
        """创建端口操作按钮组"""
        group = QGroupBox("端口信息：表格相同颜色的格子表示端口相连")
        layout = QHBoxLayout()

        # 所有端口按钮
        self.all_ports_btn = QPushButton("所有端口")
        self.all_ports_btn.setToolTip("填充为1:nports")
        self.all_ports_btn.clicked.connect(self.fill_all_ports)
        self.side_arrange_btn = QPushButton("按边排布")
        # self.side_arrange_btn.setToolTip("左半端口和右半端口分开")
        self.side_arrange_btn.clicked.connect(self.fill_side_arranged_ports)
        self.line_arrange_btn = QPushButton("按线排布")
        # self.line_arrange_btn.setToolTip("奇数和偶数端口分开")
        self.line_arrange_btn.clicked.connect(self.fill_line_arranged_ports)
        self.swap_ports_btn = QPushButton("左右交换")
        self.swap_ports_btn.clicked.connect(self.swap_ports)
        self.on_port_name = QPushButton("选择端口名")
        self.on_port_name.clicked.connect(self.fill_by_name_selected)

        layout.addWidget(self.all_ports_btn)
        layout.addWidget(self.side_arrange_btn)
        layout.addWidget(self.line_arrange_btn)
        layout.addWidget(self.swap_ports_btn)
        layout.addWidget(self.on_port_name)
        group.setLayout(layout)

        self.main_layout.addWidget(group)

    def create_table(self):
        """创建并配置表格控件"""
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["S参数文件", "级联端口序号1", "级联端口序号2"])

        # 设置列宽策略
        # header = self.table.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 第一列自适应
        # header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 第二列适应内容
        # 设置初始列宽
        self.table.setColumnWidth(0, 800)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 170)

        # 设置表格属性
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        # 设置字体
        font = QFont()
        font.setPointSize(10)
        self.table.setFont(font)

        self.main_layout.addWidget(self.table)

    def set_pair_colors(self):
        """设置端口连接对的颜色：上一行右端口和下一行左端口颜色一致"""
        row_count = self.table.rowCount()
        if row_count < 2:
            return

        # 定义一个固定色板（可以根据需要调整颜色）
        COLOR_PALETTE = [
            QColor(0, 123, 255),  # 蓝色
            QColor(40, 167, 69),  # 绿色
            QColor(255, 193, 7),  # 黄色
            QColor(220, 53, 69),  # 红色
            QColor(23, 162, 184),  # 青色
            QColor(108, 117, 125),  # 灰色
            QColor(255, 87, 34),  # 橙色
            QColor(156, 39, 176),  # 紫色
        ]

        # 设置一个颜色索引生成器
        def color_generator():
            idx = 0
            while True:
                yield COLOR_PALETTE[idx % len(COLOR_PALETTE)]
                idx += 1

        color_iter = color_generator()
        for i in range(row_count - 1):

            color = next(color_iter)  # 每次调用获取一个颜色

            # 第i行第2列（右端口）
            item_right = self.table.item(i, 2)
            if item_right is None:
                item_right = QTableWidgetItem()
                self.table.setItem(i, 2, item_right)
            item_right.setBackground(color)

            # 第i+1行第1列（左端口）
            item_left = self.table.item(i + 1, 1)
            if item_left is None:
                item_left = QTableWidgetItem()
                self.table.setItem(i + 1, 1, item_left)
            item_left.setBackground(color)

    def create_action_buttons(self):
        """创建操作按钮"""
        self.button_layout = QHBoxLayout()

        self.add_button = QPushButton("➕ 添加级联")
        self.add_button.setFixedHeight(40)
        self.add_button.clicked.connect(self.add_cascade_row)

        self.delete_button = QPushButton("🗑️ 删除选中")
        self.delete_button.setFixedHeight(40)
        self.delete_button.clicked.connect(self.delete_selected_rows)

        self.confirm_button = QPushButton("✅ 确认配置")
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.clicked.connect(self.confirm_cascade_config)

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addWidget(self.confirm_button)

        self.main_layout.addLayout(self.button_layout)

    def auto_generate_rows(self):
        """根据选中的S参数文件自动生成表格行"""
        for i, sparam in enumerate(self.selected_sparams):
            self.add_cascade_row(default_sparam=sparam, default_port=str(i + 1))
        self.set_pair_colors()  # 添加颜色

    def delete_selected_rows(self):
        """删除选中的行"""
        selected_rows = set(index.row() for index in self.table.selectedIndexes())
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return

        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def add_cascade_row(self, default_sparam=None, default_port=None):
        """添加一行级联配置"""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # S参数文件下拉框 (第0列)
        combo = QComboBox()
        combo.addItems(self.selected_sparams)
        if default_sparam:
            index = combo.findText(default_sparam)
            if index >= 0:
                combo.setCurrentIndex(index)
        self.table.setCellWidget(row, 0, combo)

        # 级联端口序号1 (第1列)
        port1_item = QTableWidgetItem(default_port if default_port else "")
        port1_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, port1_item)

        # 级联端口序号2 (第2列) - 新增初始化
        port2_item = QTableWidgetItem("")
        port2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 2, port2_item)

        self.table.scrollToBottom()
        self.set_pair_colors()  # 添加颜色

    def fill_all_ports(self):
        """在选中的单元格中填充1:nports格式数据"""
        try:
            # 获取所有选中单元格的行列索引
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                return

            for index in selected_indexes:
                row = index.row()
                column = index.column()
                # 跳过无效行
                if row >= self.table.rowCount():
                    continue

                # 只处理特定列（示例为第0列）
                if column == 0:
                    combo = self.table.cellWidget(row, 0)
                    if not combo:
                        continue

                # 解析S参数文件名的端口数（如xxx.s2p → 2）
                combo = self.table.cellWidget(row, 0)
                sparam_file = combo.currentText()

                nports = int(sparam_file.split('.')[-1][1:-1])
                # 在当前单元格填充"1:nports"
                if self.table.item(row, column):
                    self.table.item(row, column).setText(f"1:{nports}")
                else:
                    new_item = QTableWidgetItem(f"1:{nports}")
                    self.table.setItem(row, column, new_item)

        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def fill_side_arranged_ports(self):
        """按边排布端口"""
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not selected_rows:
            return

        for row in selected_rows:
            if row >= self.table.rowCount():
                continue

            # 获取S参数文件名
            combo = self.table.cellWidget(row, 0)
            sparam_file = combo.currentText()

            # 从文件名推断端口数（假设格式为*.sNp）
            try:
                nports = int(sparam_file.split('.')[-1][1:-1])
                half = nports//2
                self.table.item(row, 1).setText(f"1:{half}")
                self.table.item(row, 2).setText(f"{half+1}:{nports}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def fill_line_arranged_ports(self):
        """按线排布端口"""
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not selected_rows:
            return

        for row in selected_rows:
            if row >= self.table.rowCount():
                continue

            # 获取S参数文件名
            combo = self.table.cellWidget(row, 0)
            sparam_file = combo.currentText()

            # 从文件名推断端口数（假设格式为*.sNp）
            try:
                nports = int(sparam_file.split('.')[-1][1:-1])
                self.table.item(row, 1).setText(f"1:2:{nports-1}")
                self.table.item(row, 2).setText(f"2:2:{nports}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def swap_ports(self):
        """交换两行的端口设置"""
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        try:
            for row in rows:
                port1 = self.table.item(row, 1).text()
                port2 = self.table.item(row, 2).text()
                print(port1)
                print(port2)
                self.table.item(row, 1).setText(port2)
                self.table.item(row, 2).setText(port1)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"自动设置端口错误:\n{str(e)}")

    def fill_by_name_selected(self):
        """在选中的单元格中填充选中的端口序号"""
        try:
            # 获取所有选中单元格的行列索引
            selected_indexes = self.table.selectedIndexes()
            if not selected_indexes:
                return

            for index in selected_indexes:
                row = index.row()
                column = index.column()
                # 跳过无效行
                if row >= self.table.rowCount():
                    continue

                # 只处理特定列（示例为第0列）
                if column == 0:
                    combo = self.table.cellWidget(row, 0)
                    if not combo:
                        continue

                # 解析S参数文件名的端口数（如xxx.s2p → 2）
                combo = self.table.cellWidget(row, 0)
                sparam_file = combo.currentText()
                print(sparam_file)
                selected_ports = check_and_set_port_names(self.parent, [sparam_file])
                if selected_ports:
                    text_str = " ".join(map(str, selected_ports))
                    self.table.item(row, column).setText(text_str)


        except Exception as e:
            show_error(self, f"填充端口数据出错: {str(e)}")

    def confirm_cascade_config(self):
        """确认级联配置"""
        # if not validate_inputs(self):
        #     return

        try:
            self.cascade_configs = []

            for row in range(self.table.rowCount()):
                # 获取S参数文件名
                combo = self.table.cellWidget(row, 0)
                sparam_file = combo.currentText()

                # 获取端口号
                ports_left = parse_port_input(self.table.item(row, 1).text())
                ports_right = parse_port_input(self.table.item(row, 2).text())
                # 空检查
                if not ports_left or not ports_right:
                    QMessageBox.warning(self, "错误", f"第 {row + 1} 行端口设置不完整")
                    return
                # 添加到配置列表
                self.cascade_configs.append({
                    'sparam_file': sparam_file,
                    'ports_left': ports_left,
                    'ports_right': ports_right
                })

            # 执行连接对检查
            for i in range(len(self.cascade_configs) - 1):
                right_len = len(self.cascade_configs[i]['ports_right'])
                next_left_len = len(self.cascade_configs[i + 1]['ports_left'])
                if right_len != next_left_len:
                    QMessageBox.critical(
                        self,
                        "端口不匹配",
                        f"第 {i + 1} 行右端口数为 {right_len}，\n"
                        f"但第 {i + 2} 行左端口数为 {next_left_len}，不匹配！"
                    )
                    return

            if not self.cascade_configs:
                QMessageBox.warning(self, "错误", "没有可用的级联设置")
                return

            # 打印设置数据（实际使用时可以替换为其他处理逻辑）
            print("级联配置数据:")
            for config in self.cascade_configs:
                print(f"S参数文件: {config['sparam_file']}")
                print(f"级联端口——左{config['ports_left']}，右{config['ports_right']}")

            # 接受对话框并关闭
            self.accept()

        except:
            show_error(self, "生成配置时出错")

    def get_result(self):
        """获取结果数据"""
        return self.cascade_configs


if __name__ == "__main__":
    # 测试代码
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # 模拟选中的S参数文件列表
    selected_sparams = [
        "device1.s2p",
        "device2.s4p",
        "filter.s2p"
    ]

    dialog = SParamCascadeDialog(selected_sparams=selected_sparams)
    dialog.finished.connect(app.quit)  # 对话框关闭时退出应用

    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("返回结果:", dialog.get_result())

    sys.exit(app.exec())
