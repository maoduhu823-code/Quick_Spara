"""
评价与反馈模块。

本文件独立承载用户主动提交的评价&反馈问卷；用户身份登记和使用时长统计
继续由 usage_tracker.py 承载。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import socket
import sys

from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QRadioButton, QVBoxLayout, QWidget,
)

try:
    from .collection_config import (
        APP_VERSION,
        DEFAULT_REQUEST_DIMENSION,
        DEFAULT_REQUEST_IMPORTANCE,
        DEFAULT_REQUEST_URGENCY,
        EFFICIENCY_OPTIONS,
        EMPTY_COMBO_TEXT,
        FEEDBACK_HEADERS,
        FEEDBACK_INTRO,
        FEEDBACK_WINDOW_TITLE,
        OVERALL_EFFICIENCY_HELP,
        OVERALL_EFFICIENCY_NOTE_PLACEHOLDER,
        OVERALL_EFFICIENCY_TITLE,
        POINT_EFFICIENCY_HELP,
        POINT_EFFICIENCY_NOTE_PLACEHOLDER,
        POINT_EFFICIENCY_TITLE,
        REQUEST_DIMENSION_OPTIONS,
        REQUEST_GROUP_TITLE,
        REQUEST_IMPORTANCE_OPTIONS,
        REQUEST_TEXT_PLACEHOLDER,
        REQUEST_URGENCY_OPTIONS,
        USAGE_INTENSITY_OPTIONS,
        USAGE_INTENSITY_TITLE,
    )
    from .path_config import (
        DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM,
        LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM,
    )
    from .record_writer import configured_paths, submit_record_async
    from .usage_tracker import get_usage_profile
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from QS_runtime_services.collection_config import (
        APP_VERSION,
        DEFAULT_REQUEST_DIMENSION,
        DEFAULT_REQUEST_IMPORTANCE,
        DEFAULT_REQUEST_URGENCY,
        EFFICIENCY_OPTIONS,
        EMPTY_COMBO_TEXT,
        FEEDBACK_HEADERS,
        FEEDBACK_INTRO,
        FEEDBACK_WINDOW_TITLE,
        OVERALL_EFFICIENCY_HELP,
        OVERALL_EFFICIENCY_NOTE_PLACEHOLDER,
        OVERALL_EFFICIENCY_TITLE,
        POINT_EFFICIENCY_HELP,
        POINT_EFFICIENCY_NOTE_PLACEHOLDER,
        POINT_EFFICIENCY_TITLE,
        REQUEST_DIMENSION_OPTIONS,
        REQUEST_GROUP_TITLE,
        REQUEST_IMPORTANCE_OPTIONS,
        REQUEST_TEXT_PLACEHOLDER,
        REQUEST_URGENCY_OPTIONS,
        USAGE_INTENSITY_OPTIONS,
        USAGE_INTENSITY_TITLE,
    )
    from QS_runtime_services.path_config import (
        DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM,
        LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM,
    )
    from QS_runtime_services.record_writer import configured_paths, submit_record_async
    from QS_runtime_services.usage_tracker import get_usage_profile


# 评价&反馈记录路径统一在 QS_runtime_services/path_config.py 中配置。


class FeedbackDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(FEEDBACK_WINDOW_TITLE)
        self.setMinimumSize(1020, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        intro = QLabel(FEEDBACK_INTRO)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # 评价（左）和反馈（右）并排布局
        columns = QHBoxLayout()
        columns.setSpacing(16)

        # 左列：评价
        eval_col = QVBoxLayout()
        eval_col.setSpacing(12)

        usage_group, self.usage_intensity_group = self._choice_group(
            USAGE_INTENSITY_TITLE, "", USAGE_INTENSITY_OPTIONS
        )
        eval_col.addWidget(usage_group)

        point_group, self.point_efficiency_group = self._choice_group(
            POINT_EFFICIENCY_TITLE, POINT_EFFICIENCY_HELP, EFFICIENCY_OPTIONS
        )
        self.point_efficiency_note = self._note_edit(
            POINT_EFFICIENCY_NOTE_PLACEHOLDER
        )
        point_group.layout().addWidget(self.point_efficiency_note)
        eval_col.addWidget(point_group)

        overall_group, self.overall_efficiency_group = self._choice_group(
            OVERALL_EFFICIENCY_TITLE, OVERALL_EFFICIENCY_HELP, EFFICIENCY_OPTIONS
        )
        self.overall_efficiency_note = self._note_edit(
            OVERALL_EFFICIENCY_NOTE_PLACEHOLDER
        )
        overall_group.layout().addWidget(self.overall_efficiency_note)
        eval_col.addWidget(overall_group)

        eval_col.addStretch()
        columns.addLayout(eval_col, 1)

        # 右列：反馈
        request_group = QGroupBox(REQUEST_GROUP_TITLE)
        request_layout = QFormLayout()
        request_layout.setContentsMargins(12, 14, 12, 12)
        request_layout.setHorizontalSpacing(16)
        request_layout.setVerticalSpacing(10)

        self.request_importance_combo = self._combo_with_empty(
            REQUEST_IMPORTANCE_OPTIONS, DEFAULT_REQUEST_IMPORTANCE
        )
        self.request_urgency_combo = self._combo_with_empty(
            REQUEST_URGENCY_OPTIONS, DEFAULT_REQUEST_URGENCY
        )
        self.request_dimension_combo = self._combo_with_empty(
            REQUEST_DIMENSION_OPTIONS, DEFAULT_REQUEST_DIMENSION
        )
        self.request_text_edit = self._note_edit(REQUEST_TEXT_PLACEHOLDER)
        self.request_text_edit.setFixedHeight(92)

        request_layout.addRow("重要度:", self.request_importance_combo)
        request_layout.addRow("紧急度:", self.request_urgency_combo)
        request_layout.addRow("维度:", self.request_dimension_combo)
        request_layout.addRow("需求描述:", self.request_text_edit)
        request_group.setLayout(request_layout)
        columns.addWidget(request_group, 1)

        layout.addLayout(columns)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("提交反馈")
        if cancel_button:
            cancel_button.setText("取消")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def feedback(self) -> dict[str, str]:
        return {
            "usage_intensity": self._checked_text(self.usage_intensity_group),
            "point_efficiency": self._checked_text(self.point_efficiency_group),
            "point_efficiency_note": self.point_efficiency_note.toPlainText().strip(),
            "overall_efficiency": self._checked_text(self.overall_efficiency_group),
            "overall_efficiency_note": self.overall_efficiency_note.toPlainText().strip(),
            "request_importance": self._combo_value(self.request_importance_combo),
            "request_urgency": self._combo_value(self.request_urgency_combo),
            "request_dimension": self._combo_value(self.request_dimension_combo),
            "request_text": self.request_text_edit.toPlainText().strip(),
        }

    def _choice_group(
        self, title: str, help_text: str, options: list[str]
    ) -> tuple[QGroupBox, QButtonGroup]:
        group_box = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(12, 14, 12, 12)
        group_layout.setSpacing(8)
        if help_text:
            help_label = QLabel(help_text)
            help_label.setWordWrap(True)
            help_label.setStyleSheet("color: #666;")
            group_layout.addWidget(help_label)

        row = QHBoxLayout()
        row.setSpacing(12)
        button_group = QButtonGroup(self)
        button_group.setExclusive(True)
        for option in options:
            button = QRadioButton(option)
            button.setMinimumHeight(28)
            button_group.addButton(button)
            row.addWidget(button)
        row.addStretch()
        group_layout.addLayout(row)
        group_box.setLayout(group_layout)
        return group_box, button_group

    def _note_edit(self, placeholder: str) -> QPlainTextEdit:
        edit = QPlainTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(72)
        return edit

    def _combo_with_empty(self, options: list[str], default: str = "") -> QComboBox:
        combo = QComboBox()
        combo.addItems([EMPTY_COMBO_TEXT] + options)
        if default in options:
            combo.setCurrentText(default)
        combo.setFixedHeight(30)
        return combo

    def _checked_text(self, group: QButtonGroup) -> str:
        button = group.checkedButton()
        return button.text() if button else ""

    def _combo_value(self, combo: QComboBox) -> str:
        value = combo.currentText().strip()
        return "" if value == EMPTY_COMBO_TEXT else value

    def _accept_if_valid(self) -> None:
        feedback = self.feedback()
        text_fields = (
            "usage_intensity", "point_efficiency", "point_efficiency_note",
            "overall_efficiency", "overall_efficiency_note", "request_text",
        )
        if not any(feedback.get(key) for key in text_fields):
            QMessageBox.warning(self, "信息不完整", "请至少填写一项评价或反馈内容。")
            return
        self.accept()


def show_feedback_dialog(parent: QWidget | None = None) -> None:
    dialog = FeedbackDialog(parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    feedback = dialog.feedback()
    append_feedback(feedback)
    QMessageBox.information(
        parent,
        "提交成功",
        "感谢反馈~我们会尽快处理，如需加急请直接welink联系开发者",
    )


def append_feedback(feedback: dict[str, str]) -> None:
    profile = get_usage_profile()
    row = [
        _format_dt(_now()),
        profile.get("user_name", ""),
        profile.get("host_name", socket.gethostname()),
        profile.get("department", ""),
        profile.get("lm_group", ""),
        profile.get("pl_group", ""),
        profile.get("project_name", ""),
        feedback.get("usage_intensity", ""),
        feedback.get("point_efficiency", ""),
        feedback.get("point_efficiency_note", ""),
        feedback.get("overall_efficiency", ""),
        feedback.get("overall_efficiency_note", ""),
        feedback.get("request_importance", ""),
        feedback.get("request_urgency", ""),
        feedback.get("request_dimension", ""),
        feedback.get("request_text", ""),
        APP_VERSION,
    ]
    submit_record_async(
        record_name="评价&反馈",
        sheet_name="评价反馈",
        headers=FEEDBACK_HEADERS,
        row=row,
        local_inbox_dirs=configured_paths(
            LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM, _app_base_dir()
        ),
        developer_inbox_dirs=configured_paths(
            DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM, _app_base_dir()
        ),
    )


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _now() -> datetime:
    return datetime.now().astimezone()


def _format_dt(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


def _run_feedback_preview() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = FeedbackDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("评价&反馈测试提交结果：")
        print(feedback_to_pretty_text(dialog.feedback()))
    else:
        print("评价&反馈测试已取消。")
    return 0


def feedback_to_pretty_text(feedback: dict[str, str]) -> str:
    lines = [f"{key}: {value}" for key, value in feedback.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(_run_feedback_preview())
