from __future__ import annotations

from qtpy.QtWidgets import QPushButton

from QS_domain.display_config import FACET_OPTIONS

from .fixtures import ensure_viewer, select_files
from .harness import SmokeContext
from .widget_tools import (
    button_inventory,
    fill_all_line_edits,
    find_button,
    set_combo_text,
)


MODULE = "main"


def run(ctx: SmokeContext) -> None:
    viewer = ensure_viewer(ctx)
    ctx.step(MODULE, "button inventory",
             lambda: ctx.report.ok(MODULE, "buttons",
                                   ", ".join(button_inventory(viewer))))
    ctx.step(MODULE, "placeholder line edits",
             lambda: fill_all_line_edits(viewer))
    ctx.step(MODULE, "main dropdown full product",
             lambda: _exercise_main_dropdown_product(ctx, viewer))
    ctx.step(MODULE, "port placeholder format combinations",
             lambda: _exercise_port_formats(ctx, viewer))
    ctx.step(MODULE, "plot each parameter facet",
             lambda: _exercise_plot_facets(ctx, viewer))
    ctx.step(MODULE, "file operation buttons",
             lambda: _exercise_file_buttons(ctx, viewer))
    ctx.step(MODULE, "information buttons",
             lambda: _exercise_info_buttons(ctx, viewer))
    ctx.step(MODULE, "module opener buttons are covered",
             lambda: _record_module_openers(ctx, viewer))


def _exercise_main_dropdown_product(ctx: SmokeContext, viewer) -> int:
    count = 0
    for display_idx in range(viewer.file_display_combo.count()):
        viewer.file_display_combo.setCurrentIndex(display_idx)
        for mapping_idx in range(viewer.mapping_combo.count()):
            viewer.mapping_combo.setCurrentIndex(mapping_idx)
            for x_idx in range(viewer.xscale_combo.count()):
                viewer.xscale_combo.setCurrentIndex(x_idx)
                for y_idx in range(viewer.yscale_combo.count()):
                    viewer.yscale_combo.setCurrentIndex(y_idx)
                    for param_type, facets in FACET_OPTIONS.items():
                        set_combo_text(viewer.param_type_combo, param_type)
                        ctx.process_events(2)
                        for facet in facets:
                            set_combo_text(viewer.facet_combo, facet)
                            ctx.process_events(2)
                            count += 1
    ctx.report.ok(MODULE, "main dropdown combinations",
                  f"{count} dropdown combinations traversed")
    return count


def _exercise_port_formats(ctx: SmokeContext, viewer) -> int:
    select_files(viewer, [0])
    viewer.freG_input.setText("5")
    set_combo_text(viewer.param_type_combo, "S参数")
    set_combo_text(viewer.facet_combo, "幅度(dB)")
    cases = [
        ("1", "2", "一 一对应"),
        ("1 2", "2 3", "一 一对应"),
        ("1:2", "3:4", "一 一对应"),
        ("1:2:3", "2:2:4", "一 一对应"),
        ("1 2", "3 4", "交叉映射"),
    ]
    for p1, p2, mapping in cases:
        viewer.port1_input.setText(p1)
        viewer.port2_input.setText(p2)
        set_combo_text(viewer.mapping_combo, mapping)
        viewer.plot_s_parameters()
        ctx.process_events(10)
        ctx.close_mpl_figures()
    return len(cases)


def _exercise_plot_facets(ctx: SmokeContext, viewer) -> int:
    select_files(viewer, [0])
    viewer.port1_input.setText("1")
    viewer.port2_input.setText("2")
    viewer._td_tr_edit.setText("50")
    viewer._td_dt_edit.setText("25")
    viewer._td_z0_edit.setText("50")
    viewer.freG_input.setText("5")
    count = 0
    for param_type, facets in FACET_OPTIONS.items():
        set_combo_text(viewer.param_type_combo, param_type)
        ctx.process_events(5)
        facet_iter = facets[:1] if ctx.args.quick else facets
        for facet in facet_iter:
            set_combo_text(viewer.facet_combo, facet)
            viewer.plot_s_parameters()
            ctx.process_events(10)
            ctx.close_mpl_figures()
            count += 1
    return count


def _exercise_file_buttons(ctx: SmokeContext, viewer) -> None:
    select_files(viewer, [0])
    viewer.open_button.click()
    ctx.process_events()
    select_files(viewer, [0])
    viewer.save_button.click()
    ctx.process_events()
    viewer.read_button.click()
    ctx.process_events()
    if viewer.file_list.count() > 1:
        select_files(viewer, [viewer.file_list.count() - 1])
        viewer.delete_button.click()
        ctx.process_events()
    select_files(viewer, [0])


def _exercise_info_buttons(ctx: SmokeContext, viewer) -> None:
    select_files(viewer, [0])
    viewer.port1_input.setText("1")
    viewer.port2_input.setText("2")
    viewer.port_select_btn.click()
    ctx.process_events()
    ctx.close_mpl_figures()
    # 「参数信息」下拉菜单的 3 个动作
    for action in (viewer.act_freq_axis, viewer.act_basic_info, viewer.act_freq_slice):
        action.trigger()
        ctx.process_events()
        ctx.close_mpl_figures()
    for text in ["清除缓存", "清除输出", "评价 | 需求反馈"]:
        button = find_button(viewer, text)
        if isinstance(button, QPushButton):
            button.click()
            ctx.process_events()


def _record_module_openers(ctx: SmokeContext, viewer) -> None:
    labels = [
        viewer.port_management_button.text(),
        viewer.cascade_button.text(),
        viewer.diff_button.text(),
        viewer.analysis_btn.text(),
        viewer.ripple_btn.text(),
    ]
    if hasattr(viewer, "td_analysis_btn"):
        labels.append(viewer.td_analysis_btn.text())
    ctx.report.ok(MODULE, "module opener buttons",
                  "covered by module cases: " + ", ".join(labels))
