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
    from .record_writer import append_excel_row_async, configured_paths
    from .usage_tracker import get_usage_profile
    from .version_manager import APP_VERSION
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from runtime_services.record_writer import append_excel_row_async, configured_paths
    from runtime_services.usage_tracker import get_usage_profile
    from runtime_services.version_manager import APP_VERSION


APP_NAME = "Quick_Sparam"

# 修改这里来指定评价&反馈 Excel 的本地备选路径。
FEEDBACK_LOCAL_EXCEL_PATHS_BY_PLATFORM = {
    "win32": [
        r"./Public/Quick_Sparam_feedback.xlsx",
        r"%APPDATA%\Quick_Sparam\Quick_Sparam_feedback.xlsx",
    ],
    "linux": [
        r"./Public/Quick_Sparam_feedback.xlsx",
        r"~/.config/Quick_Sparam/Quick_Sparam_feedback.xlsx",
    ],
    "default": [
        r"./Public/Quick_Sparam_feedback.xlsx",
    ],
}

# 修改这里来指定开发者收集 Excel 的远程/共享备选路径。
FEEDBACK_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = {
    "win32": [
        r"\\10.114.193.143\Public_userdata_collect\Quick_Sparam_feedback.xlsx",
        r"\\10.114.193.143\Public\Quick_Sparam_feedback.xlsx",
    ],
    "linux": [
        r"/data/Storage_pisi/w00810255/Qs/Public/Quick_Sparam_feedback.xlsx",
    ],
    "default": [],
}

# ===== 评价&反馈问卷配置区：后续主要改这里 =====
USAGE_INTENSITY_OPTIONS = [
    "<1h/周", "1-2h/周", "2-3h/周", "3-5h/周", ">5h/周",
]
EFFICIENCY_OPTIONS = [
    "<25%", "25%-50%", "50%-75%", "75%-100%", ">100%",
]
POINT_EFFICIENCY_HELP = "为了实现某个工作流程，例如：xxx、yyy"
OVERALL_EFFICIENCY_HELP = "为了实现项目所需的所有工作流程，例如：xxx、yyy"

REQUEST_IMPORTANCE_OPTIONS = ["低", "中", "高", "非常高"]
REQUEST_URGENCY_OPTIONS = ["不急", "一般", "较急", "非常紧急"]
REQUEST_DIMENSION_OPTIONS = [
    "UI交互", "Bug反馈", "工作流增加", "单点功能增加", "功能改进",
    "性能/稳定性", "结果可信度", "文档/示例", "其他",
]

FEEDBACK_HEADERS = [
    "提交时间", "用户姓名", "主机名", "部门", "LM大组", "PL小组", "应用项目名",
    "使用强度", "单点效率提高程度", "单点效率补充", "整体效率提高程度",
    "整体效率补充", "需求重要度", "需求紧急度", "需求维度", "需求描述",
    "App版本",
]

EMPTY_COMBO_TEXT = "未选择"


class FeedbackDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("评价&反馈")
        self.setMinimumSize(640, 720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        intro = QLabel("欢迎补充软件使用评价和后续需求，便于内部版本规划和优先级判断。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        usage_group, self.usage_intensity_group = self._choice_group(
            "使用强度", "", USAGE_INTENSITY_OPTIONS
        )
        layout.addWidget(usage_group)

        point_group, self.point_efficiency_group = self._choice_group(
            "单点效率提高程度", POINT_EFFICIENCY_HELP, EFFICIENCY_OPTIONS
        )
        self.point_efficiency_note = self._note_edit("可补充具体工作流、对比方式或估算依据，非必填")
        point_group.layout().addWidget(self.point_efficiency_note)
        layout.addWidget(point_group)

        overall_group, self.overall_efficiency_group = self._choice_group(
            "整体效率提高程度", OVERALL_EFFICIENCY_HELP, EFFICIENCY_OPTIONS
        )
        self.overall_efficiency_note = self._note_edit("可补充项目级收益、节省环节或协作收益，非必填")
        overall_group.layout().addWidget(self.overall_efficiency_note)
        layout.addWidget(overall_group)

        request_group = QGroupBox("需求反馈（非必填）")
        request_layout = QFormLayout()
        request_layout.setContentsMargins(12, 14, 12, 12)
        request_layout.setHorizontalSpacing(16)
        request_layout.setVerticalSpacing(10)

        self.request_importance_combo = self._combo_with_empty(REQUEST_IMPORTANCE_OPTIONS)
        self.request_urgency_combo = self._combo_with_empty(REQUEST_URGENCY_OPTIONS)
        self.request_dimension_combo = self._combo_with_empty(REQUEST_DIMENSION_OPTIONS)
        self.request_text_edit = self._note_edit(
            "请描述具体场景、当前痛点、期望结果；如果是bug，请尽量写复现步骤"
        )
        self.request_text_edit.setFixedHeight(92)

        request_layout.addRow("重要度:", self.request_importance_combo)
        request_layout.addRow("紧急度:", self.request_urgency_combo)
        request_layout.addRow("维度:", self.request_dimension_combo)
        request_layout.addRow("需求描述:", self.request_text_edit)
        request_group.setLayout(request_layout)
        layout.addWidget(request_group)

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

    def _combo_with_empty(self, options: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems([EMPTY_COMBO_TEXT] + options)
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
        missing = [
            label for key, label in (
                ("usage_intensity", "使用强度"),
                ("point_efficiency", "单点效率提高程度"),
                ("overall_efficiency", "整体效率提高程度"),
            )
            if not feedback.get(key)
        ]
        if missing:
            QMessageBox.warning(self, "信息不完整", "请填写：" + "、".join(missing))
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
        "感谢反馈，已开始后台写入记录，不影响软件使用。",
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
    append_excel_row_async(
        record_name="评价&反馈",
        sheet_name="评价反馈",
        headers=FEEDBACK_HEADERS,
        row=row,
        local_paths=configured_paths(FEEDBACK_LOCAL_EXCEL_PATHS_BY_PLATFORM, _app_base_dir()),
        developer_paths=configured_paths(
            FEEDBACK_DEVELOPER_EXCEL_PATHS_BY_PLATFORM, _app_base_dir()
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
