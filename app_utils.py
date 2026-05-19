import sys
import os
import traceback
import numpy as np
from qtpy.QtWidgets import QMessageBox, QDialog, QApplication


# === 错误提示 ===

def show_error(parent, context_message=""):
    """显示带行号的错误弹窗"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    last_frame = traceback.extract_tb(exc_traceback)[-1]
    error_msg = (
        f"{context_message}\n\n"
        f"🛑 错误位置:\n"
        f"文件: {last_frame.filename}\n"
        f"行号: {last_frame.lineno}\n"
        f"函数: {last_frame.name}\n\n"
        f"💥 错误详情:\n{str(exc_value)}"
    )
    QMessageBox.critical(parent, '错误', error_msg)


# === 路径工具 ===

def resource_path(relative_path: str) -> str:
    """获取资源的绝对路径，适用于开发环境和 PyInstaller 打包环境。"""
    from QS_infra.resource_path import resource_path as _rp
    return _rp(relative_path)


# === matplotlib 配置 ===

def configure_matplotlib() -> None:
    """设置平台相关中文字体及负号渲染，幂等可重复调用。"""
    import matplotlib
    matplotlib.rcParams['axes.unicode_minus'] = False
    if sys.platform == 'win32':
        matplotlib.rcParams['font.sans-serif'] = ['SimHei']
        matplotlib.rcParams.setdefault('mathtext.fontset', 'stix')
    else:
        matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']


def _get_pyplot():
    import matplotlib.pyplot as plt
    return plt


# === 绘图辅助 ===

def freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode="max"):
    """在频段内标注极值点，返回标注点和极值点信息"""
    mark_info = []
    worst_info = []
    for fG_mark in mark_freqGs:
        idx = np.abs(freqG - fG_mark).argmin()
        actual_freq = freqG[idx]
        actual_value = y_data[idx]
        mark_info.append({'freq': float(actual_freq), 'value': float(actual_value)})

        mask = (freqG <= fG_mark)
        band_freqG = freqG[mask]
        band_data = y_data[mask]

        if worst_mode == "max":
            worst_idx = np.argmax(band_data)
        else:
            worst_idx = np.argmin(band_data)
        worst_freqG = band_freqG[worst_idx]
        worst_value = band_data[worst_idx]

        ax.plot(worst_freqG, worst_value, 'ro', markersize=5)
        worst_info.append({'freq': float(worst_freqG), 'value': float(worst_value)})
    return mark_info, worst_info


def plot_main_curves(results_data, data_mode):
    """绘制主曲线（原始曲线和拟合曲线）"""
    plt = _get_pyplot()
    configure_matplotlib()
    plt.figure()
    for data in results_data:
        plt.plot(data['freqG_range'], data['s_param_range'], label=data['label'])
        plt.plot(data['freqG_range'], data['fitted_curve'], '--',
                 label=f"{data['label']} (拟合)")
        plt.plot(data['max_ripple_freqG'], data['s_param_range'][data['max_ripple_index']], 'o')
        if data['formula']:
            plt.annotate(
                data['formula'],
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', va='top',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.3))
        plt.legend()
        plt.xlabel('频率 (GHz)')
        plt.ylabel(data_mode)
        plt.title('S参数曲线与拟合曲线')
        plt.grid(True)
        plt.show()


# === 交互式 legend ===

def attach_interactive_legend(ax, *, lines=None, draggable=True,
                              on_legend_pick=None,
                              toggle_on_pick=True, context_menu=True,
                              toolbar_button=True,
                              toggle_key='ctrl+l', legend_kwargs=None):
    """让 ax 上的 legend 支持拖拽 / 联动高亮 / 切显示 / 右键菜单 / 整体开关 / 工具栏按钮。

    交互一览：
    - 拖拽         鼠标按住 legend 框拖动（matplotlib 原生）
    - 左键单击     调用 on_legend_pick(orig_line)；未传则降级为切换该曲线显示
                  （legend 的小色块和文字都响应单击）
    - Shift+左键   切换该曲线显示/隐藏（条目变半透明指示）
    - 右键 legend  弹菜单：「修改标注名…」（批量改名对话框）/「隐藏 legend」
    - 工具栏       NavigationToolbar 末尾追加「图例」按钮，菜单同上加上「显示/隐藏」
    - toggle_key   切换整个 legend 显示/隐藏，默认 'ctrl+l'（避开 matplotlib 默认 l/L 对数轴）

    Args:
        ax: matplotlib Axes
        lines: 纳入控制的曲线列表；None 表示 ax 上所有非下划线 label 的 Line2D
        on_legend_pick: 单击 legend 条目时调用 fn(orig_line)；常用于联动曲线高亮
        toggle_on_pick: True 时允许 Shift+单击切显示
        context_menu: 是否启用右键菜单
        toolbar_button: 是否往 NavigationToolbar 加「图例」按钮（无工具栏时静默跳过）
        toggle_key: 整体开关快捷键；None 禁用
        legend_kwargs: 透传给 ax.legend()

    Returns:
        legend 对象，或 None（无可用条目时）。
    """
    fig = ax.figure
    if lines is None:
        lines = [ln for ln in ax.get_lines()
                 if ln.get_label() and not ln.get_label().startswith('_')]
    if not lines:
        return None

    legend = ax.legend(**(legend_kwargs or {}))
    if legend is None:
        return None

    if draggable:
        legend.set_draggable(True)

    legend_lines = legend.get_lines()
    legend_texts = legend.get_texts()
    label_to_line = {ln.get_label(): ln for ln in lines}

    # 双向映射：marker 和 text 都映射到原曲线 + 同条目的 text（用于 alpha 同步）
    artist_to_orig = {}
    artist_to_legtext = {}
    interactive = toggle_on_pick or on_legend_pick is not None
    for legline, legtext in zip(legend_lines, legend_texts):
        orig = label_to_line.get(legtext.get_text())
        if orig is None:
            continue
        artist_to_orig[legline] = orig
        artist_to_orig[legtext] = orig
        artist_to_legtext[legline] = legtext
        artist_to_legtext[legtext] = legtext
        if interactive:
            legline.set_picker(5)
            legtext.set_picker(5)

    def _toggle_visibility(legtext, orig):
        visible = not orig.get_visible()
        orig.set_visible(visible)
        legtext.set_alpha(1.0 if visible else 0.4)
        for legline, lt in artist_to_legtext.items():
            if lt is legtext and hasattr(legline, 'set_alpha') and legline is not legtext:
                legline.set_alpha(1.0 if visible else 0.25)

    if interactive:
        def _on_pick(event):
            orig = artist_to_orig.get(event.artist)
            if orig is None:
                return
            legtext = artist_to_legtext.get(event.artist)
            me = event.mouseevent
            is_shift = bool(me and me.key and 'shift' in me.key.lower())
            if is_shift and toggle_on_pick and legtext is not None:
                _toggle_visibility(legtext, orig)
            elif on_legend_pick is not None:
                on_legend_pick(orig)
            elif toggle_on_pick and legtext is not None:
                _toggle_visibility(legtext, orig)
            else:
                return
            fig.canvas.draw_idle()
        fig.canvas.mpl_connect('pick_event', _on_pick)

    if context_menu:
        def _on_button(event):
            if event.button != 3 or event.x is None or event.y is None:
                return
            if not legend.get_visible():
                return
            try:
                bbox = legend.get_window_extent()
            except Exception:
                return
            if not bbox.contains(event.x, event.y):
                return
            _show_legend_context_menu(legend, fig, event, _legend_rename_map(legend, lines))
        fig.canvas.mpl_connect('button_press_event', _on_button)

    if toggle_key:
        _target_key = str(toggle_key).lower()

        def _on_key(event):
            if event.key and event.key.lower() == _target_key:
                legend.set_visible(not legend.get_visible())
                fig.canvas.draw_idle()
        fig.canvas.mpl_connect('key_press_event', _on_key)

    if toolbar_button:
        attach_legend_toolbar_button(fig, legend, lines)

    return legend


def attach_legend_toolbar_button(fig, legend, lines):
    """往 NavigationToolbar 末尾加一个「图例」按钮，点开弹菜单。

    与右键菜单功能一致再加一项整体切换；非 Qt 后端或没有工具栏时静默返回 None。
    """
    try:
        from qtpy.QtWidgets import QToolButton, QMenu
        from qtpy.QtCore import Qt
    except ImportError:
        return None
    canvas = fig.canvas
    toolbar = getattr(canvas, 'toolbar', None)
    if toolbar is None:
        manager = getattr(canvas, 'manager', None)
        toolbar = getattr(manager, 'toolbar', None) if manager is not None else None
    if toolbar is None or not hasattr(toolbar, 'addWidget'):
        return None

    button = QToolButton(toolbar)
    button.setText('图例')
    button.setToolTip('图例操作：显示/隐藏、修改标注名')
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

    menu = QMenu(button)
    toggle_action = menu.addAction('显示/隐藏 legend')
    rename_action = menu.addAction('修改标注名…')

    def _toggle():
        legend.set_visible(not legend.get_visible())
        fig.canvas.draw_idle()

    def _rename():
        apply_legend_batch_rename(_legend_rename_map(legend, lines), fig)

    toggle_action.triggered.connect(_toggle)
    rename_action.triggered.connect(_rename)
    button.setMenu(menu)

    toolbar.addSeparator()
    toolbar.addWidget(button)
    return button


def _legend_rename_map(legend, lines):
    """返回 [(legtext, orig_line)] 列表，供批量改名对话框使用。"""
    label_to_line = {ln.get_label(): ln for ln in lines}
    pairs = []
    for legtext in legend.get_texts():
        orig = label_to_line.get(legtext.get_text())
        if orig is not None:
            pairs.append((legtext, orig))
    return pairs


def _show_legend_context_menu(legend, fig, event, rename_pairs):
    """右键 legend 区域时调用：弹 QMenu，两个动作。"""
    try:
        from qtpy.QtWidgets import QMenu
        from qtpy.QtCore import QPoint
    except ImportError:
        return
    app = QApplication.instance()
    if app is None:
        return
    canvas = fig.canvas
    menu = QMenu(canvas)
    rename_action = menu.addAction('修改标注名…')
    hide_action = menu.addAction('隐藏 legend')
    # mpl event.y 起点在底部；Qt 起点在顶部
    local = QPoint(int(event.x), int(canvas.height() - event.y))
    global_pos = canvas.mapToGlobal(local)
    chosen = menu.exec(global_pos)
    if chosen is rename_action:
        apply_legend_batch_rename(rename_pairs, fig)
    elif chosen is hide_action:
        legend.set_visible(False)
        fig.canvas.draw_idle()


def apply_legend_batch_rename(rename_pairs, fig):
    """弹批量改名对话框，确认后把每条 legend text + 原曲线 label 都改掉。

    rename_pairs: [(legtext_artist, original_line2d), ...]
    """
    try:
        from qtpy.QtWidgets import (
            QDialog, QVBoxLayout, QFormLayout, QLineEdit,
            QDialogButtonBox, QLabel,
        )
    except ImportError:
        return
    if QApplication.instance() is None or not rename_pairs:
        return

    dialog = QDialog()
    dialog.setWindowTitle('修改 legend 标注名')
    dialog.setMinimumWidth(640)
    outer = QVBoxLayout(dialog)
    outer.addWidget(QLabel('可一次修改所有图例文字；留空保持原值。'))
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    rows = []
    for legtext, orig in rename_pairs:
        current = legtext.get_text()
        label = QLabel(current)
        label.setWordWrap(True)
        label.setMinimumWidth(140)
        label.setMaximumWidth(260)
        edit = QLineEdit(current)
        edit.setMinimumWidth(420)
        form.addRow(label, edit)
        rows.append((legtext, orig, current, edit))
    outer.addLayout(form)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    outer.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    changed = False
    for legtext, orig, current, edit in rows:
        new = edit.text().strip()
        if not new or new == current:
            continue
        legtext.set_text(new)
        orig.set_label(new)
        changed = True
    if changed:
        fig.canvas.draw_idle()


def plot_residuals(results_data, data_mode):
    """绘制残差曲线"""
    plt = _get_pyplot()
    configure_matplotlib()
    plt.figure()
    for data in results_data:
        plt.plot(data['freqG_range'], data['residuals'],
                 label=f"{data['label']} (ripple)")
    plt.legend()
    plt.xlabel('频率 (GHz)')
    plt.ylabel(data_mode)
    plt.title('S参数拟合Ripple')
    plt.grid(True)
    plt.show()


# === 端口UI工具 ===

def check_and_set_port_names(parent, file_list, network_service=None):
    """弹出端口选择器，返回排序后的端口索引列表(从1开始)，失败返回None。

    parent         : 任意 QWidget，作为对话框的父控件
    file_list      : 文件名/key 列表
    network_service: 可选 NetworkService；未传时降级回 parent.get_network()
    """
    from QS_dialogs.port_selector import PortSelector
    from QS_dialogs.port_name import PortNameDialog

    if not file_list:
        QMessageBox.warning(parent, "警告", "请先选择S参数文件")
        return None

    if len(file_list) > 1:
        QMessageBox.information(parent, "提示", "检测到多文件选择，将使用第一个文件的端口")

    try:
        if network_service is not None:
            network = network_service.get_network(file_list[0])
        else:
            network = parent.get_network(file_list[0])
    except Exception as e:
        QMessageBox.critical(parent, "错误", f"文件加载失败: {str(e)}")
        return None

    if not network.port_names:
        dialog = PortNameDialog(parent, network.nports, file_list[0])
        network.port_names = dialog.get_port_names()
        if not network.port_names:
            return None

    result, indices = PortSelector.select_ports(network.port_names, parent)
    if result != QDialog.DialogCode.Accepted or not indices:
        return None

    indices.sort()
    selected_names = [network.port_names[i - 1] for i in indices]
    print(f"\n=== 端口选择结果 ===")
    print(f"• 索引: {indices}\n• 名称: {', '.join(selected_names)}")
    QApplication.clipboard().setText(" ".join(map(str, indices)))
    return indices
