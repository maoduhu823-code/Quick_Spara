from __future__ import annotations

from itertools import product

from .fixtures import ensure_viewer, select_files
from .harness import SmokeContext
from qtpy.QtWidgets import QPushButton

from .widget_tools import button_inventory


MODULE = "time_domain"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "time domain dialog",
             lambda: _exercise_time_domain(ctx, viewer))


def _exercise_time_domain(ctx: SmokeContext, viewer) -> int:
    from QS_dialogs.time_domain import TimeDomainDialog

    select_files(viewer, [0])
    dialog = TimeDomainDialog(
        viewer.s_data,
        viewer,
        network_service=viewer._net_svc,
        get_selected_files=viewer.get_selected_file_keys,
    )
    ctx.show_widget(dialog, 940, 720)
    ctx.report.ok(MODULE, "buttons", ", ".join(button_inventory(dialog)))

    for button in [b for b in dialog.findChildren(QPushButton) if b.text() == "自动"]:
        button.click()
        ctx.process_events(5)

    count = 0
    wave_buttons = list(dialog._wf_btn_group.buttons())
    combo_ranges = [
        range(dialog._win_combo.count()),
        range(dialog._map_combo.count()),
        range(dialog._unit_combo.count()),
    ]
    for waveform_button in wave_buttons:
        waveform_button.setChecked(True)
        dialog._on_waveform_changed(waveform_button)
        for win_idx, map_idx, unit_idx in product(*combo_ranges):
            if ctx.args.quick and count > 3:
                break
            dialog._win_combo.setCurrentIndex(win_idx)
            dialog._map_combo.setCurrentIndex(map_idx)
            dialog._unit_combo.setCurrentIndex(unit_idx)
            dialog._port1_edit.setText("1")
            dialog._port2_edit.setText("1" if dialog._current_waveform() == "TDR" else "2")
            dialog._clear_port_pairs()
            dialog._add_port_pairs()
            dialog._run_plot()
            ctx.process_events(10)
            ctx.close_mpl_figures()
            count += 1
        if ctx.args.quick and count > 3:
            break

    dialog._clear_port_pairs()
    dialog._port1_edit.setText("1")
    dialog._port2_edit.setText("2")
    dialog._add_port_pairs()
    if dialog._port_list.count() > 0:
        dialog._port_list.item(0).setSelected(True)
    dialog._delete_port_pairs()
    dialog._clear_port_pairs()
    ctx.close_widget(dialog)
    ctx.report.ok(MODULE, "wave/window/map/unit combinations",
                  f"{count} action combinations traversed")
    return count
