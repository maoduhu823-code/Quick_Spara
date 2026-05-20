"""
用户问卷和使用时长统计模块。

复制到其他 app 时，主要修改 QS_runtime_services/collection_config.py 和
QS_runtime_services/path_config.py。
"""

from __future__ import annotations

from datetime import datetime
import getpass
import json
from pathlib import Path
import socket
import sys
import time
from typing import Any

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QVBoxLayout, QWidget,
)

try:
    from .collection_config import (
        APP_VERSION,
        DEPARTMENT_OPTIONS,
        DEPARTMENT_OTHER_PLACEHOLDER,
        LM_GROUP_OPTIONS,
        LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT,
        LM_GROUP_OTHER_PLACEHOLDER,
        OTHER_OPTION,
        PL_GROUP_OPTIONS_BY_LM,
        PL_GROUP_OPTIONS_FOR_OTHER_LM,
        PL_GROUP_OTHER_PLACEHOLDER,
        PRIMARY_DEPARTMENT,
        PROFILE_PROMPT_MODE,
        PROFILE_SCHEMA_VERSION,
        PROJECT_FIELD_LABEL,
        PROJECT_PLACEHOLDER,
        REQUIRED_PROFILE_FIELDS,
        USAGE_HEADERS,
        USAGE_SURVEY_INTRO,
        USAGE_SURVEY_WINDOW_TITLE,
        USER_DATA_HEADERS,
        USER_NAME_PLACEHOLDER,
    )
    from .path_config import (
        DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM,
        LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM,
        profile_local_path,
        profile_remote_path,
    )
    from .record_writer import configured_paths, submit_record_async
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from QS_runtime_services.collection_config import (
        APP_VERSION,
        DEPARTMENT_OPTIONS,
        DEPARTMENT_OTHER_PLACEHOLDER,
        LM_GROUP_OPTIONS,
        LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT,
        LM_GROUP_OTHER_PLACEHOLDER,
        OTHER_OPTION,
        PL_GROUP_OPTIONS_BY_LM,
        PL_GROUP_OPTIONS_FOR_OTHER_LM,
        PL_GROUP_OTHER_PLACEHOLDER,
        PRIMARY_DEPARTMENT,
        PROFILE_PROMPT_MODE,
        PROFILE_SCHEMA_VERSION,
        PROJECT_FIELD_LABEL,
        PROJECT_PLACEHOLDER,
        REQUIRED_PROFILE_FIELDS,
        USAGE_HEADERS,
        USAGE_SURVEY_INTRO,
        USAGE_SURVEY_WINDOW_TITLE,
        USER_DATA_HEADERS,
        USER_NAME_PLACEHOLDER,
    )
    from QS_runtime_services.path_config import (
        DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM,
        LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM,
        profile_local_path,
        profile_remote_path,
    )
    from QS_runtime_services.record_writer import configured_paths, submit_record_async

# 用户资料、问卷和使用记录 inbox 路径统一在 QS_runtime_services/path_config.py 中配置。


class UsageTracker:
    def __init__(self) -> None:
        self.start_dt = _now()
        self.start_monotonic = time.monotonic()
        self._usage_written = False

    def ensure_profile(self, parent: Any = None) -> dict[str, str]:
        profile = _load_profile()
        if PROFILE_PROMPT_MODE != "every_start" and _profile_complete(profile):
            self._append_survey(profile)
            # 本机已有完整 profile：分发模式下检查共享盘是否有同步副本，没有则推送。
            _auto_sync_profile_to_remote(profile, parent=parent)
            return profile

        dialog = UsageSurveyDialog(parent, profile)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            print("提示：用户信息问卷未填写完成，下次启动会继续提示。")
            return profile

        profile = dialog.profile()
        remote_failed = False
        try:
            result = _save_profile(profile)
            remote_failed = result.remote_attempted and not result.remote_succeeded
        except Exception as exc:
            print(f"提示：用户资料本地保存失败，下次启动可能继续提示填写。错误: {exc}")
        self._append_survey(profile)
        if remote_failed:
            _show_remote_sync_warning(parent)
        return profile

    def write_usage_log(self) -> None:
        if self._usage_written:
            return
        self._usage_written = True

        profile = _load_profile()
        end_dt = _now()
        elapsed_seconds = max(0, int(round(time.monotonic() - self.start_monotonic)))
        row = [
            profile.get("host_name", socket.gethostname()),
            _format_dt(self.start_dt),
            _format_dt(end_dt),
        ]
        _append_usage_record_async("使用记录", "使用记录", USAGE_HEADERS, row)
        print(f"本次使用时长: {_format_duration(elapsed_seconds)}")

    def _append_survey(self, profile: dict[str, str]) -> None:
        row = [
            _format_dt(_now()),
            profile.get("host_name", socket.gethostname()),
            profile.get("user_name", getpass.getuser()),
            profile.get("department", ""),
            profile.get("lm_group", ""),
            profile.get("pl_group", ""),
            profile.get("project_name", ""),
            APP_VERSION,
        ]
        _append_usage_record_async("用户信息", "用户信息", USER_DATA_HEADERS, row)


class UsageSurveyDialog(QDialog):
    def __init__(self, parent: Any = None, profile: dict[str, str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(USAGE_SURVEY_WINDOW_TITLE)
        self.setMinimumSize(500, 620)
        profile = profile or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        intro = QLabel(USAGE_SURVEY_INTRO)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(4)

        # 身份信息表单
        id_form = QFormLayout()
        id_form.setContentsMargins(0, 4, 0, 0)
        id_form.setHorizontalSpacing(18)
        id_form.setVerticalSpacing(16)
        id_form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.user_edit = QLineEdit(profile.get("user_name", ""))
        self.user_edit.setPlaceholderText(USER_NAME_PLACEHOLDER)
        self.department_combo = QComboBox()
        self.department_other_edit = QLineEdit()
        self.department_other_edit.setPlaceholderText(DEPARTMENT_OTHER_PLACEHOLDER)
        self.lm_group_combo = QComboBox()
        self.lm_group_other_edit = QLineEdit()
        self.lm_group_other_edit.setPlaceholderText(LM_GROUP_OTHER_PLACEHOLDER)
        self.pl_group_combo = QComboBox()
        self.pl_group_other_edit = QLineEdit()
        self.pl_group_other_edit.setPlaceholderText(PL_GROUP_OTHER_PLACEHOLDER)

        for widget in (
            self.user_edit,
            self.department_combo,
            self.department_other_edit,
            self.lm_group_combo,
            self.lm_group_other_edit,
            self.pl_group_combo,
            self.pl_group_other_edit,
        ):
            widget.setFixedHeight(32)

        id_form.addRow("用户姓名:", self.user_edit)
        id_form.addRow("部门:", self._inline_row(self.department_combo, self.department_other_edit))
        id_form.addRow("LM大组:", self._inline_row(self.lm_group_combo, self.lm_group_other_edit))
        id_form.addRow("PL小组:", self._inline_row(self.pl_group_combo, self.pl_group_other_edit))
        layout.addLayout(id_form)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # 项目信息表单
        proj_form = QFormLayout()
        proj_form.setContentsMargins(0, 0, 0, 0)
        proj_form.setHorizontalSpacing(18)
        proj_form.setVerticalSpacing(16)
        self.project_edit = QPlainTextEdit(profile.get("project_name", ""))
        self.project_edit.setPlaceholderText(PROJECT_PLACEHOLDER)
        self.project_edit.setFixedHeight(72)
        proj_form.addRow(PROJECT_FIELD_LABEL, self.project_edit)
        layout.addLayout(proj_form)
        layout.addStretch()

        self.department_combo.currentTextChanged.connect(self._on_department_changed)
        self.lm_group_combo.currentTextChanged.connect(self._on_lm_group_changed)
        self.pl_group_combo.currentTextChanged.connect(self._on_pl_group_changed)
        self._load_profile_values(profile)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("提交")
        if cancel_button:
            cancel_button.setText("稍后填写")
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(8)
        layout.addWidget(buttons)

    def profile(self) -> dict[str, str]:
        return {
            "schema_version": str(PROFILE_SCHEMA_VERSION),
            "user_name": self.user_edit.text().strip(),
            "host_name": socket.gethostname(),
            "department": self._current_value(
                self.department_combo, self.department_other_edit),
            "lm_group": self._current_value(
                self.lm_group_combo, self.lm_group_other_edit),
            "pl_group": self._current_value(
                self.pl_group_combo, self.pl_group_other_edit),
            "project_name": self.project_edit.toPlainText().strip(),
            "updated_at": _format_dt(_now()),
        }

    def _load_profile_values(self, profile: dict[str, str]) -> None:
        self._set_combo_options(
            self.department_combo, DEPARTMENT_OPTIONS, profile.get("department", "")
        )
        self._sync_other_edit(
            self.department_combo, self.department_other_edit, profile.get("department", "")
        )
        self._on_department_changed()
        self._set_combo_options(
            self.lm_group_combo, self._lm_options(), profile.get("lm_group", "")
        )
        self._sync_other_edit(
            self.lm_group_combo, self.lm_group_other_edit, profile.get("lm_group", "")
        )
        self._on_lm_group_changed()
        self._set_combo_options(
            self.pl_group_combo, self._pl_options(), profile.get("pl_group", "")
        )
        self._sync_other_edit(
            self.pl_group_combo, self.pl_group_other_edit, profile.get("pl_group", "")
        )

    def _on_department_changed(self) -> None:
        self._sync_other_edit(self.department_combo, self.department_other_edit)
        self._set_combo_options(self.lm_group_combo, self._lm_options())
        self._sync_other_edit(self.lm_group_combo, self.lm_group_other_edit)
        self._on_lm_group_changed()

    def _on_lm_group_changed(self) -> None:
        self._sync_other_edit(self.lm_group_combo, self.lm_group_other_edit)
        self._set_combo_options(self.pl_group_combo, self._pl_options())
        self._sync_other_edit(self.pl_group_combo, self.pl_group_other_edit)

    def _on_pl_group_changed(self) -> None:
        self._sync_other_edit(self.pl_group_combo, self.pl_group_other_edit)

    def _lm_options(self) -> list[str]:
        department = self._current_value(
            self.department_combo, self.department_other_edit)
        if department == PRIMARY_DEPARTMENT:
            return LM_GROUP_OPTIONS
        return LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT

    def _pl_options(self) -> list[str]:
        lm_group = self._current_value(self.lm_group_combo, self.lm_group_other_edit)
        return PL_GROUP_OPTIONS_BY_LM.get(lm_group, PL_GROUP_OPTIONS_FOR_OTHER_LM)

    def _inline_row(self, combo: QComboBox, edit: QLineEdit) -> QWidget:
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(combo)
        row_layout.addWidget(edit)
        return container

    def _set_combo_options(
        self, combo: QComboBox, options: list[str], value: str = ""
    ) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(options)
        if value and value in options:
            combo.setCurrentText(value)
        elif value and OTHER_OPTION in options:
            combo.setCurrentText(OTHER_OPTION)
        elif options:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _sync_other_edit(
        self, combo: QComboBox, edit: QLineEdit, value: str = ""
    ) -> None:
        is_other = combo.currentText() == OTHER_OPTION
        edit.setVisible(is_other)
        if value and value not in [combo.itemText(i) for i in range(combo.count())]:
            edit.setText(value)
        elif not is_other:
            edit.clear()

    def _current_value(self, combo: QComboBox, edit: QLineEdit) -> str:
        if combo.currentText() == OTHER_OPTION:
            return edit.text().strip()
        return combo.currentText().strip()

    def _accept_if_valid(self) -> None:
        profile = self.profile()
        missing = [
            label for key, label in (
                ("department", "部门"),
                ("lm_group", "LM大组"),
                ("pl_group", "PL小组"),
                ("project_name", "应用项目名"),
            )
            if not profile.get(key)
        ]
        if missing:
            QMessageBox.warning(self, "信息不完整", "请填写：" + "、".join(missing))
            return
        self.accept()


def _profile_complete(profile: dict[str, str]) -> bool:
    return all(profile.get(field, "").strip() for field in REQUIRED_PROFILE_FIELDS)


def get_usage_profile() -> dict[str, str]:
    return _load_profile()


class _ProfileSaveResult:
    """_save_profile 的返回值。本机模式下 remote_attempted=False。"""
    __slots__ = ("local_path", "remote_attempted", "remote_succeeded", "remote_error")

    def __init__(self) -> None:
        self.local_path: Path | None = None
        self.remote_attempted: bool = False
        self.remote_succeeded: bool = False
        self.remote_error: str = ""


def _load_profile() -> dict[str, str]:
    """只读本机 usage_profile.json。共享盘版本不参与判断"本地是否已填"，
    避免别人在共享盘留下的资料污染本机首启动逻辑。"""
    local = _local_profile_path()
    if local.exists():
        try:
            with local.open("r", encoding="utf-8") as f:
                profile = json.load(f)
            base = _base_profile()
            base.update({k: str(v) for k, v in profile.items()})
            return base
        except Exception as exc:
            print(f"提示：本机用户资料读取失败：{local}，错误: {exc}")
    return _base_profile()


def _save_profile(profile: dict[str, str]) -> _ProfileSaveResult:
    """先写本机（失败抛错，本机存档是硬要求），再尝试写远端（best effort）。"""
    result = _ProfileSaveResult()
    local = _local_profile_path()
    try:
        local.parent.mkdir(parents=True, exist_ok=True)
        with local.open("w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        result.local_path = local
        print(f"用户资料已保存到本机: {local}")
    except Exception as exc:
        raise RuntimeError(f"本机保存失败 {local}: {exc}")

    remote = _remote_profile_path()
    if remote is not None:
        result.remote_attempted = True
        try:
            remote.parent.mkdir(parents=True, exist_ok=True)
            with remote.open("w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            result.remote_succeeded = True
            print(f"用户资料已同步到共享盘: {remote}")
        except Exception as exc:
            result.remote_error = str(exc)
            print(f"提示：用户资料同步到共享盘失败：{exc}")
    return result


def _auto_sync_profile_to_remote(profile: dict[str, str], parent: Any = None) -> None:
    """本机已有完整 profile，但远端没有 → 推送一次。失败时弹一次性警告。"""
    remote = _remote_profile_path()
    if remote is None:
        return
    if remote.exists():
        return
    try:
        remote.parent.mkdir(parents=True, exist_ok=True)
        with remote.open("w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        print(f"用户资料已同步到共享盘: {remote}")
    except Exception as exc:
        print(f"提示：用户资料同步到共享盘失败：{exc}")
        _show_remote_sync_warning(parent)


def _show_remote_sync_warning(parent: Any) -> None:
    QMessageBox.warning(
        parent,
        "用户资料",
        "用户资料已保存到本机，但无法自动发送到共享盘。\n"
        "请联系管理员添加共享路径权限。",
    )


def _local_profile_path() -> Path:
    raw = profile_local_path()
    path = Path(raw)
    if not path.is_absolute():
        path = _app_base_dir() / path
    return path


def _remote_profile_path() -> Path | None:
    raw = profile_remote_path()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = _app_base_dir() / path
    return path


def _base_profile() -> dict[str, str]:
    return {
        "schema_version": str(PROFILE_SCHEMA_VERSION),
        "user_name": "",
        "host_name": socket.gethostname(),
        "department": "",
        "lm_group": "",
        "pl_group": "",
        "project_name": "",
    }


def _append_usage_record_async(
    record_name: str, sheet_name: str, headers: list[str], row: list[Any]
) -> None:
    submit_record_async(
        record_name=record_name,
        sheet_name=sheet_name,
        headers=headers,
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


def _format_duration(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _run_usage_survey_preview() -> int:
    from qtpy.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dialog = UsageSurveyDialog(profile=_base_profile())
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("问卷测试提交结果：")
        print(json.dumps(dialog.profile(), ensure_ascii=False, indent=2))
    else:
        print("问卷测试已取消。")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_usage_survey_preview())
