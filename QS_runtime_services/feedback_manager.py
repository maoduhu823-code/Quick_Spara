"""
评价与反馈模块。

本文件独立承载用户主动提交的评价&反馈问卷；用户身份登记和使用时长统计
继续由 usage_tracker.py 承载。
"""

from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import socket
import sys
import uuid

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeySequence, QPainter
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
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
        OVERALL_SCORE_TITLE,
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
        OVERALL_SCORE_TITLE,
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


class StarRatingWidget(QWidget):
    ratingChanged = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rating = 0.0
        self.setFixedSize(150, 34)
        self.setMouseTracking(True)
        self.setToolTip("点击星星评分，左/右半星分别按 0.5 分递增")

    def rating(self) -> float:
        return self._rating

    def set_rating(self, value: float) -> None:
        bounded = max(0.0, min(5.0, round(float(value) * 2.0) / 2.0))
        if bounded != self._rating:
            self._rating = bounded
            self.update()
            self.ratingChanged.emit(self._rating)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont()
        font.setPointSize(22)
        painter.setFont(font)

        star_w = self._star_width()
        for index in range(5):
            x = index * star_w
            rect = QRectF(x, 0, star_w, self.height())
            painter.setPen(QColor("#c7c7c7"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "★")

            fill = max(0.0, min(1.0, self._rating - index))
            if fill <= 0.0:
                continue
            painter.save()
            painter.setClipRect(QRectF(x, 0, star_w * fill, self.height()))
            painter.setPen(QColor("#f5b301"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "★")
            painter.restore()
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_rating(self._position_rating(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def _position_rating(self, x: float) -> float:
        if x <= 0:
            return 0.0
        raw = x / self._star_width()
        return max(0.0, min(5.0, math.ceil(raw * 2.0) / 2.0))

    def _star_width(self) -> float:
        return self.width() / 5.0


class AttachmentListWidget(QListWidget):
    def __init__(self, paste_callback, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paste_callback = paste_callback

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self._paste_callback()
            event.accept()
            return
        super().keyPressEvent(event)


class FeedbackDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(FEEDBACK_WINDOW_TITLE)
        self.setMinimumSize(1020, 520)
        self.attachment_paths: list[Path] = []

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

        score_group = QGroupBox(OVERALL_SCORE_TITLE)
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(12, 12, 12, 10)
        score_layout.setSpacing(10)
        self.overall_score_widget = StarRatingWidget()
        self.overall_score_label = QLabel("0.0 / 5")
        self.overall_score_label.setMinimumWidth(56)
        self.overall_score_widget.ratingChanged.connect(
            lambda value: self.overall_score_label.setText(f"{value:.1f} / 5")
        )
        score_layout.addWidget(self.overall_score_widget)
        score_layout.addWidget(self.overall_score_label)
        score_layout.addStretch()
        score_group.setLayout(score_layout)
        eval_col.addWidget(score_group)

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
        self.request_text_edit.setFixedHeight(68)
        attachment_widget = self._attachment_widget()

        request_layout.addRow("重要度:", self.request_importance_combo)
        request_layout.addRow("紧急度:", self.request_urgency_combo)
        request_layout.addRow("维度:", self.request_dimension_combo)
        request_layout.addRow("需求描述:", self.request_text_edit)
        request_layout.addRow("附件:", attachment_widget)
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

    def feedback(self) -> dict[str, object]:
        return {
            "usage_intensity": self._checked_text(self.usage_intensity_group),
            "overall_score": f"{self.overall_score_widget.rating():.1f}",
            "point_efficiency": self._checked_text(self.point_efficiency_group),
            "point_efficiency_note": self.point_efficiency_note.toPlainText().strip(),
            "overall_efficiency": self._checked_text(self.overall_efficiency_group),
            "overall_efficiency_note": self.overall_efficiency_note.toPlainText().strip(),
            "request_importance": self._combo_value(self.request_importance_combo),
            "request_urgency": self._combo_value(self.request_urgency_combo),
            "request_dimension": self._combo_value(self.request_dimension_combo),
            "request_text": self.request_text_edit.toPlainText().strip(),
            "attachments": [str(path) for path in self.attachment_paths],
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
        edit.setFixedHeight(54)
        return edit

    def _combo_with_empty(self, options: list[str], default: str = "") -> QComboBox:
        combo = QComboBox()
        combo.addItems([EMPTY_COMBO_TEXT] + options)
        if default in options:
            combo.setCurrentText(default)
        combo.setFixedHeight(30)
        return combo

    def _attachment_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.attachment_list = AttachmentListWidget(self._paste_clipboard_image)
        self.attachment_list.setFixedHeight(86)
        self.attachment_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.attachment_list.setToolTip("可添加截图、数据文件或复现材料；支持 Ctrl+V 粘贴图片")
        layout.addWidget(self.attachment_list)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        add_button = QPushButton("添加附件")
        paste_button = QPushButton("粘贴图片")
        remove_button = QPushButton("移除选中")
        add_button.clicked.connect(self._add_attachments)
        paste_button.clicked.connect(self._paste_clipboard_image)
        remove_button.clicked.connect(self._remove_selected_attachments)
        button_row.addWidget(add_button)
        button_row.addWidget(paste_button)
        button_row.addWidget(remove_button)
        button_row.addStretch()
        layout.addLayout(button_row)
        return widget

    def _add_attachments(self) -> None:
        file_names, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "选择附件",
            "",
            "所有文件 (*.*)",
        )
        if not file_names:
            return

        seen = {self._path_key(path) for path in self.attachment_paths}
        for file_name in file_names:
            path = Path(file_name)
            key = self._path_key(path)
            if key in seen or not path.is_file():
                continue
            self.attachment_paths.append(path)
            seen.add(key)
        self._refresh_attachment_list()

    def _paste_clipboard_image(self) -> None:
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            QMessageBox.information(self, "没有图片", "剪贴板中没有可粘贴的图片。")
            return

        target_dir = _app_base_dir() / "data_feedback" / "pasted_attachments"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"clipboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        target_path = target_dir / file_name
        if not image.save(str(target_path), "PNG"):
            QMessageBox.warning(self, "粘贴失败", "剪贴板图片保存失败。")
            return

        self.attachment_paths.append(target_path)
        self._refresh_attachment_list()
        self.attachment_list.setCurrentRow(len(self.attachment_paths) - 1)

    def _remove_selected_attachments(self) -> None:
        selected_rows = sorted(
            {self.attachment_list.row(item) for item in self.attachment_list.selectedItems()},
            reverse=True,
        )
        for row in selected_rows:
            if 0 <= row < len(self.attachment_paths):
                del self.attachment_paths[row]
        self._refresh_attachment_list()

    def _refresh_attachment_list(self) -> None:
        self.attachment_list.clear()
        for path in self.attachment_paths:
            item = QListWidgetItem(f"{path.name} ({self._format_file_size(path)})")
            item.setToolTip(str(path))
            self.attachment_list.addItem(item)

    def _path_key(self, path: Path) -> str:
        try:
            return str(path.resolve()).casefold()
        except OSError:
            return str(path).casefold()

    def _format_file_size(self, path: Path) -> str:
        try:
            size = path.stat().st_size
        except OSError:
            return "大小未知"
        units = ["B", "KB", "MB", "GB"]
        value = float(size)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
            value /= 1024
        return f"{size}B"

    def _checked_text(self, group: QButtonGroup) -> str:
        button = group.checkedButton()
        return button.text() if button else ""

    def _combo_value(self, combo: QComboBox) -> str:
        value = combo.currentText().strip()
        return "" if value == EMPTY_COMBO_TEXT else value

    def _accept_if_valid(self) -> None:
        feedback = self.feedback()
        text_fields = (
            "overall_score", "usage_intensity", "point_efficiency", "point_efficiency_note",
            "overall_efficiency", "overall_efficiency_note", "request_text",
        )
        has_text = any(
            feedback.get(key) and feedback.get(key) != "0.0"
            for key in text_fields
        )
        if not has_text:
            if feedback.get("attachments"):
                self.accept()
                return
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


def append_feedback(feedback: dict[str, object]) -> None:
    profile = get_usage_profile()
    attachments = _feedback_attachments(feedback)
    row = [
        _format_dt(_now()),
        profile.get("user_name", ""),
        profile.get("host_name", socket.gethostname()),
        profile.get("department", ""),
        profile.get("lm_group", ""),
        profile.get("pl_group", ""),
        profile.get("project_name", ""),
        feedback.get("overall_score", ""),
        feedback.get("usage_intensity", ""),
        feedback.get("point_efficiency", ""),
        feedback.get("point_efficiency_note", ""),
        feedback.get("overall_efficiency", ""),
        feedback.get("overall_efficiency_note", ""),
        feedback.get("request_importance", ""),
        feedback.get("request_urgency", ""),
        feedback.get("request_dimension", ""),
        feedback.get("request_text", ""),
        _attachment_names(attachments),
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
        attachments=attachments,
    )


def _feedback_attachments(feedback: dict[str, object]) -> list[Path]:
    raw_attachments = feedback.get("attachments", [])
    if not isinstance(raw_attachments, list):
        return []
    paths: list[Path] = []
    for raw_path in raw_attachments:
        if raw_path:
            paths.append(Path(str(raw_path)))
    return paths


def _attachment_names(paths: list[Path]) -> str:
    return "; ".join(path.name for path in paths)


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


def feedback_to_pretty_text(feedback: dict[str, object]) -> str:
    lines = [f"{key}: {value}" for key, value in feedback.items()]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(_run_feedback_preview())
