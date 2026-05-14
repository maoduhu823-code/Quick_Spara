from __future__ import annotations

from .fixtures import ensure_viewer, selected_file_keys
from .harness import SmokeContext
from .widget_tools import button_inventory


MODULE = "ripple"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "ripple dialog combo actions",
             lambda: _exercise_ripple(ctx, viewer))


def _exercise_ripple(ctx: SmokeContext, viewer) -> int:
    from QS_dialogs.ripple import RippleFitDialog

    files = selected_file_keys(viewer)[:1]
    dialog = RippleFitDialog(viewer, files, network_service=viewer._net_svc)
    ctx.show_widget(dialog)
    ctx.report.ok(MODULE, "buttons", ", ".join(button_inventory(dialog)))
    network = viewer.get_network(files[0])
    stop_ghz = max(float(network.f[-1]) / 1e9, 0.1)
    stop_text = f"{min(stop_ghz, 10.0):.4g}"
    dialog.port1_input.setText("1")
    dialog.port2_input.setText("2")
    dialog.start_freq_input.setText("0")
    dialog.stop_freq_input.setText(stop_text)

    count = 0
    for data_index in range(dialog.data_mode_combo.count()):
        dialog.data_mode_combo.setCurrentIndex(data_index)
        method_range = range(dialog.fit_method.count())
        if ctx.args.quick:
            method_range = range(min(1, dialog.fit_method.count()))
        for method_index in method_range:
            dialog.fit_method.setCurrentIndex(method_index)
            ctx.process_events(5)
            dialog._run_analysis()
            ctx.process_events(10)
            ctx.close_mpl_figures()
            count += 1

    ctx.report.ok(MODULE, "data mode / fit method combinations",
                  f"{count} action combinations traversed")
    ctx.close_widget(dialog)
    return count
