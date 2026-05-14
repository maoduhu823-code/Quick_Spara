from __future__ import annotations

from .fixtures import ensure_viewer, first_network
from .harness import SmokeContext
from .widget_tools import button_inventory, fill_all_line_edits


MODULE = "diff"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "dialog combinations",
             lambda: _exercise_dialog(ctx, first_network(viewer).nports))


def _exercise_dialog(ctx: SmokeContext, nports: int) -> int:
    from QS_dialogs.se2diff import DiffConversionDialog

    dialog = DiffConversionDialog(nports)
    ctx.show_widget(dialog)
    ctx.report.ok(MODULE, "buttons", ", ".join(button_inventory(dialog)))
    fill_all_line_edits(dialog)
    count = 0

    for port_mode in ["inside", "inline"]:
        dialog.line_logic_radio.setChecked(True)
        dialog.inside_radio.setChecked(port_mode == "inside")
        dialog.inline_radio.setChecked(port_mode == "inline")
        for partial in [False, True]:
            dialog.partial_diff_radio.setChecked(partial)
            dialog.diff_lines_edit.setText("1 2")
            for output_full in [False, True]:
                dialog.sdd_only_radio.setChecked(not output_full)
                dialog.full_mixed_radio.setChecked(output_full)
                params = dialog.get_conversion_params()
                if not params:
                    raise AssertionError("line logic conversion params are empty")
                count += 1

    dialog.port_logic_radio.setChecked(True)
    dialog.custom_input.setText("1 3 2 4")
    for output_full in [False, True]:
        dialog.sdd_only_radio.setChecked(not output_full)
        dialog.full_mixed_radio.setChecked(output_full)
        params = dialog.get_conversion_params()
        if not params:
            raise AssertionError("port logic conversion params are empty")
        count += 1

    dialog.accept()
    ctx.close_widget(dialog)
    ctx.report.ok(MODULE, "radio/input combinations",
                  f"{count} combinations traversed")
    return count
