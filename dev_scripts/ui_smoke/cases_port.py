from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QDialogButtonBox

from .fixtures import ensure_viewer, first_network, selected_file_keys
from .harness import SmokeContext
from .widget_tools import button_inventory, click_button


MODULE = "port"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "management dispatch buttons",
             lambda: _exercise_management(ctx, viewer))
    ctx.step(MODULE, "z0 edit dialog",
             lambda: _exercise_z0_edit(ctx, viewer))
    ctx.step(MODULE, "port selector dialog",
             lambda: _exercise_selector(ctx, viewer))
    ctx.step(MODULE, "port reorder dialog",
             lambda: _exercise_reorder(ctx, viewer))
    ctx.step(MODULE, "port merge dialog",
             lambda: _exercise_merge(ctx, viewer))
    ctx.step(MODULE, "port reduction dialog",
             lambda: _exercise_reduction(ctx, viewer))


def _exercise_management(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_management import PortManagementDialog

    expected = {
        "编辑端口名": 1,
        "修改参考阻抗": 2,
        "端口重新排序": 3,
        "端口合并": 4,
        "重归一化/端口缩并": 5,
    }
    for text, code in expected.items():
        dialog = PortManagementDialog(viewer)
        ctx.show_widget(dialog)
        ctx.report.ok(MODULE, f"management buttons {text}",
                      ", ".join(button_inventory(dialog)))
        click_button(ctx, MODULE, dialog, text)
        if dialog.result() != code:
            raise AssertionError(f"{text} returned {dialog.result()}, expected {code}")
        ctx.close_widget(dialog)


def _exercise_z0_edit(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_management import Z0EditDialog

    dialog = Z0EditDialog(viewer, first_network(viewer))
    ctx.show_widget(dialog)
    for row in range(dialog.table.rowCount()):
        dialog.table.item(row, 2).setText("50")
    buttons = dialog.findChild(QDialogButtonBox)
    ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
    ok_button.click()
    if not dialog.get_z0_values():
        raise AssertionError("Z0 values were not collected")
    ctx.close_widget(dialog)


def _exercise_selector(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_selector import PortSelector

    port_names = first_network(viewer).port_names
    dialog = PortSelector(port_names, viewer)
    ctx.show_widget(dialog)
    click_button(ctx, MODULE, dialog, "全选")
    if not dialog.get_selected_indices():
        raise AssertionError("select all did not select ports")
    click_button(ctx, MODULE, dialog, "清除选择")
    click_button(ctx, MODULE, dialog, "全选")
    click_button(ctx, MODULE, dialog, "确定")
    ctx.close_widget(dialog)


def _exercise_reorder(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_reorder import PortOrderEditor

    dialog = PortOrderEditor(first_network(viewer).port_names, viewer)
    ctx.show_widget(dialog)
    click_button(ctx, MODULE, dialog, "重置顺序")
    order = dialog.get_ordered_ports()
    if order != list(range(1, len(order) + 1)):
        raise AssertionError(f"Unexpected reset order: {order}")
    click_button(ctx, MODULE, dialog, "确定")
    ctx.close_widget(dialog)


def _exercise_merge(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_merge import PortMergeDialog

    dialog = PortMergeDialog(viewer, selected_file_keys(viewer), network_service=viewer._net_svc)
    ctx.show_widget(dialog)
    ctx.report.ok(MODULE, "merge buttons", ", ".join(button_inventory(dialog)))
    click_button(ctx, MODULE, dialog, "➕ 添加合并组(行)")
    dialog.table.selectRow(dialog.table.rowCount() - 1)
    click_button(ctx, MODULE, dialog, "🗑️ 删除选中行")
    dialog.table.item(0, 0).setText("1 2")
    dialog.table.item(0, 1).setText("50")
    click_button(ctx, MODULE, dialog, "生成S参数")
    groups, z0 = dialog.get_result()
    if groups != [[1, 2]] or z0 != [50.0]:
        raise AssertionError(f"Unexpected merge result: {groups}, {z0}")
    ctx.close_widget(dialog)


def _exercise_reduction(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.port_reduction import PortReductionDialog

    dialog = PortReductionDialog(viewer, selected_file_keys(viewer),
                                 network_service=viewer._net_svc)
    ctx.show_widget(dialog)
    ctx.report.ok(MODULE, "reduction buttons", ", ".join(button_inventory(dialog)))
    click_button(ctx, MODULE, dialog, "按侧排布")
    click_button(ctx, MODULE, dialog, "按线排布")
    click_button(ctx, MODULE, dialog, "➕ 添加端口组(行)")
    dialog.table.selectRow(dialog.table.rowCount() - 1)
    click_button(ctx, MODULE, dialog, "🗑️ 删除端口组(行)")
    dialog.table.setRowCount(1)
    dialog.add_port_row(port_num="1 2", enabled=True)
    dialog.table.removeRow(0)
    dialog.table.item(0, 1).setText("50")
    dialog.table.item(0, 2).setText("0")
    checkbox = dialog.table.cellWidget(0, 3).findChild(QCheckBox)
    checkbox.setChecked(True)
    click_button(ctx, MODULE, dialog, "生成S参数")
    ports, z0s, disabled = dialog.get_result()
    if ports != [[1, 2]] or not z0s or disabled != [1, 2]:
        raise AssertionError(f"Unexpected reduction result: {ports}, {z0s}, {disabled}")
    ctx.close_widget(dialog)
