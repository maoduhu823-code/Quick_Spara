from __future__ import annotations

from PyQt6.QtWidgets import QComboBox

from .fixtures import ensure_viewer, selected_file_keys
from .harness import SmokeContext
from .widget_tools import button_inventory, click_button, exercise_combo_product


MODULE = "cascade"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "cascade dialog",
             lambda: _exercise_cascade(ctx, viewer))


def _exercise_cascade(ctx: SmokeContext, viewer) -> None:
    from QS_dialogs.cascade import CascadeDialog

    files = selected_file_keys(viewer)
    if len(files) < 2:
        files = files * 2
    dialog = CascadeDialog(viewer, files[:2], network_service=viewer._net_svc)
    ctx.show_widget(dialog)
    ctx.report.ok(MODULE, "buttons", ", ".join(button_inventory(dialog)))
    exercise_combo_product(ctx, MODULE, "table file combo product",
                           dialog.findChildren(QComboBox))

    dialog.table.selectAll()
    click_button(ctx, MODULE, dialog, "所有端口")
    click_button(ctx, MODULE, dialog, "按边排布")
    click_button(ctx, MODULE, dialog, "按线排布")
    click_button(ctx, MODULE, dialog, "左右交换")

    for row in range(dialog.table.rowCount()):
        dialog.table.item(row, 1).setText("1")
        dialog.table.item(row, 2).setText("2")
    click_button(ctx, MODULE, dialog, "✅ 确认配置")
    result = dialog.get_result()
    if not result:
        raise AssertionError("Cascade result is empty")
    ctx.close_widget(dialog)
