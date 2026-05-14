from __future__ import annotations

from itertools import product

from .fixtures import ensure_viewer, select_files
from .harness import SmokeContext
from .widget_tools import button_inventory


MODULE = "freq_analysis"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "frequency analysis dialog",
             lambda: _exercise_freq_analysis(ctx, viewer))


def _exercise_freq_analysis(ctx: SmokeContext, viewer) -> int:
    from QS_dialogs.freq_analysis import frequencyAnalysisDialog

    select_files(viewer, [0])
    dialog = frequencyAnalysisDialog(viewer.s_data, viewer)
    ctx.show_widget(dialog, 900, 520)
    ctx.report.ok(MODULE, "buttons", ", ".join(button_inventory(dialog)))

    count = 0
    for inside, forward, mode_index in product([True, False], [True, False], range(3)):
        dialog.inside_radio.setChecked(inside)
        dialog.inline_radio.setChecked(not inside)
        dialog.forward_radio.setChecked(forward)
        dialog.reverse_radio.setChecked(not forward)
        [dialog.power_radio, dialog.modulo_radio, dialog.vector_radio][mode_index].setChecked(True)
        dialog.update_image_display()
        ctx.process_events(5)
        count += 1
    ctx.report.ok(MODULE, "radio combinations", f"{count} combinations traversed")

    for checkbox in dialog.analysis_checks.values():
        checkbox.setChecked(False)
    first_key = next(iter(dialog.analysis_checks))
    dialog.analysis_checks[first_key].setChecked(True)
    dialog.line_input.setText("1")
    dialog.freG_input.setText("1,5,10")

    buttons = [
        dialog.specific_line_button,
        dialog.compare_button,
        dialog.bar_button,
        dialog.FrePlot_button,
        dialog.save_button,
    ]
    for button in buttons:
        button.click()
        ctx.process_events(10)
        ctx.close_mpl_figures()

    ctx.close_widget(dialog)
    return count
