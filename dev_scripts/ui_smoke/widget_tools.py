from __future__ import annotations

from itertools import product
from typing import Iterable

from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QWidget,
)

from .harness import SmokeContext


def widget_label(widget: QWidget) -> str:
    if hasattr(widget, "text") and callable(widget.text):
        text = widget.text()
        if text:
            return text
    if isinstance(widget, QLineEdit) and widget.placeholderText():
        return widget.placeholderText()
    name = widget.objectName()
    if name:
        return name
    return widget.__class__.__name__


def find_button(root: QWidget, text: str) -> QPushButton | None:
    for button in root.findChildren(QPushButton):
        if button.text() == text:
            return button
    return None


def click_button(ctx: SmokeContext, module: str, root: QWidget, text: str) -> None:
    button = find_button(root, text)
    if button is None:
        raise AssertionError(f"Button not found: {text}")
    if not button.isEnabled():
        raise AssertionError(f"Button disabled: {text}")
    button.click()
    ctx.process_events()


def all_combo_options(combo: QComboBox) -> list[str]:
    return [combo.itemText(i) for i in range(combo.count())]


def set_combo_text(combo: QComboBox, text: str) -> None:
    index = combo.findText(text)
    if index < 0:
        raise AssertionError(f"Combo option not found: {text}")
    combo.setCurrentIndex(index)


def exercise_combo_product(ctx: SmokeContext, module: str, case: str,
                           combos: Iterable[QComboBox],
                           max_combinations: int | None = None) -> int:
    combo_list = [combo for combo in combos if combo.count() > 0]
    if not combo_list:
        ctx.report.ok(module, case, "no combo boxes")
        return 0
    index_ranges = [range(combo.count()) for combo in combo_list]
    count = 0
    for indices in product(*index_ranges):
        if max_combinations is not None and count >= max_combinations:
            ctx.report.warn(module, case, f"stopped at {count} combinations")
            break
        for combo, index in zip(combo_list, indices):
            combo.setCurrentIndex(index)
        ctx.process_events(5)
        count += 1
    ctx.report.ok(module, case, f"{count} combo combinations traversed")
    return count


def fill_line_edit_from_hint(edit: QLineEdit) -> None:
    if not edit.isEnabled() or edit.isReadOnly():
        return
    hint = f"{edit.objectName()} {edit.placeholderText()} {edit.text()}".lower()
    if "1 3 2 4" in hint:
        edit.setText("1 3 2 4")
    elif "3:5" in hint or "1:2:5" in hint:
        edit.setText("1:2:3")
    elif "1:4" in hint:
        edit.setText("1:4")
    elif "端口" in hint or "port" in hint:
        edit.setText("1 2")
    elif "频点" in hint or "ghz" in hint:
        edit.setText("1,5,10")
    elif "阻抗" in hint or "z0" in hint:
        edit.setText("50")
    elif "点数" in hint or "n_points" in hint:
        edit.setText("2048")
    elif "时间" in hint or "ps" in hint:
        edit.setText("50")
    elif not edit.text():
        edit.setText("1")


def fill_all_line_edits(root: QWidget) -> int:
    count = 0
    for edit in root.findChildren(QLineEdit):
        fill_line_edit_from_hint(edit)
        count += 1
    return count


def toggle_all_checkboxes(root: QWidget) -> int:
    count = 0
    for checkbox in root.findChildren(QCheckBox):
        checkbox.setChecked(not checkbox.isChecked())
        checkbox.setChecked(not checkbox.isChecked())
        count += 1
    return count


def exercise_radio_buttons(ctx: SmokeContext, root: QWidget) -> int:
    count = 0
    for radio in root.findChildren(QRadioButton):
        if radio.isEnabled():
            radio.setChecked(True)
            ctx.process_events(5)
            count += 1
    return count


def button_inventory(root: QWidget) -> list[str]:
    labels: list[str] = []
    for button in root.findChildren(QAbstractButton):
        label = widget_label(button)
        if label:
            labels.append(label)
    return labels
