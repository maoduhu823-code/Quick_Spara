"""
用户问卷和使用时长统计模块。

复制到其他 app 时，主要修改本文件顶部的 APP_NAME 和
USAGE_EXCEL_PATH_BY_PLATFORM。
"""

from __future__ import annotations

from datetime import datetime
import getpass
import json
from pathlib import Path
import socket
import sys
import time
import uuid
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QMessageBox, QVBoxLayout,
)

try:
    from .record_writer import append_excel_row_async, configured_paths
    from .version_manager import APP_VERSION
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from runtime_services.record_writer import append_excel_row_async, configured_paths
    from runtime_services.version_manager import APP_VERSION


APP_NAME = "Quick_Sparam"

# 修改这里来指定用户资料本地 JSON 的备选路径。
PROFILE_PATHS_BY_PLATFORM = {
    "win32": [
        r"%APPDATA%\Quick_Sparam\usage_profile.json",
        r"./Public/usage_profile.json",
    ],
    "linux": [
        r"~/.config/Quick_Sparam/usage_profile.json",
        r"./Public/usage_profile.json",
    ],
    "default": [
        r"./Public/usage_profile.json",
    ],
}

# 修改这里来指定问卷和使用记录 Excel 的本地备选路径。
# 相对路径会按程序所在目录解析；打包后可把 Public 放到 exe 同级目录。
USAGE_LOCAL_EXCEL_PATHS_BY_PLATFORM = {
    "win32": [
        r"./Public/Quick_Sparam_usage.xlsx",
        r"%APPDATA%\Quick_Sparam\Quick_Sparam_usage.xlsx",
    ],
    "linux": [
        r"./Public/Quick_Sparam_usage.xlsx",
        r"~/.config/Quick_Sparam/Quick_Sparam_usage.xlsx",
    ],
    "default": [
        r"./Public/Quick_Sparam_usage.xlsx",
    ],
}

# 修改这里来指定开发者收集 Excel 的远程/共享备选路径。
USAGE_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = {
    "win32": [
        r"\\10.114.193.143\Public_userdata_collect\Quick_Sparam_usage.xlsx",
        r"\\10.114.193.143\Public\Quick_Sparam_usage.xlsx",
    ],
    "linux": [
        r"/data/Storage_pisi/w00810255/Qs/Public/Quick_Sparam_usage.xlsx",
    ],
    "default": [],
}

PROFILE_SCHEMA_VERSION = 1
# "missing_only": 本地资料缺失时才弹问卷；"every_start": 每次启动都弹出预填问卷。
PROFILE_PROMPT_MODE = "missing_only"
REQUIRED_PROFILE_FIELDS = ("department", "lm_group", "pl_group", "project_name")

# ===== 问卷选项配置区：你后续主要改这里 =====
OTHER_OPTION = "其他"
PRIMARY_DEPARTMENT = "封装SIPI开发部"
DEPARTMENT_OPTIONS = [PRIMARY_DEPARTMENT, OTHER_OPTION]
LM_GROUP_OPTIONS = ["电性能技术", "泛终端", "泛无线", "网络计算", "硬件", OTHER_OPTION]
LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT = [OTHER_OPTION]
PL_GROUP_OPTIONS_BY_LM = {
    "电性能技术": ["图灵PI", "存储技术组", OTHER_OPTION],
    "泛终端": ["无线终端", "短距离", "终端芯片", OTHER_OPTION],
    "泛无线": ["无线数字", "网络射频", "无线射频", OTHER_OPTION],
    "网络计算": ["图灵SI组", "IPNP", "光联接", OTHER_OPTION],
    "硬件": ["平台EVB硬件一组","平台EVB硬件二组", "泛无线硬件", "网络计算硬件", "互连仿真工艺", OTHER_OPTION],
}
PL_GROUP_OPTIONS_FOR_OTHER_LM = [OTHER_OPTION]

SURVEY_HEADERS = [
    "填写时间", "用户姓名", "主机名", "部门", "LM大组", "PL小组", "应用项目名",
    "App版本",
]
USAGE_HEADERS = [
    "会话ID", "用户姓名", "主机名", "部门", "LM大组", "PL小组", "应用项目名",
    "日期", "启动时间", "关闭时间", "使用秒数", "使用分钟", "使用时长", "App版本",
]


class UsageTracker:
    def __init__(self) -> None:
        self.session_id = str(uuid.uuid4())
        self.start_dt = _now()
        self.start_monotonic = time.monotonic()
        self._usage_written = False

    def ensure_profile(self, parent: Any = None) -> dict[str, str]:
        profile = _load_profile()
        if PROFILE_PROMPT_MODE != "every_start" and _profile_complete(profile):
            return profile

        dialog = UsageSurveyDialog(parent, profile)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            print("提示：用户信息问卷未填写完成，下次启动会继续提示。")
            return profile

        profile = dialog.profile()
        try:
            _save_profile(profile)
        except Exception as exc:
            print(f"提示：用户资料本地保存失败，下次启动可能继续提示填写。错误: {exc}")
        self._append_survey(profile)
        return profile

    def write_usage_log(self) -> None:
        if self._usage_written:
            return
        self._usage_written = True

        profile = _load_profile()
        end_dt = _now()
        elapsed_seconds = max(0, int(round(time.monotonic() - self.start_monotonic)))
        row = [
            self.session_id,
            profile.get("user_name", getpass.getuser()),
            profile.get("host_name", socket.gethostname()),
            profile.get("department", ""),
            profile.get("lm_group", ""),
            profile.get("pl_group", ""),
            profile.get("project_name", ""),
            self.start_dt.strftime("%Y-%m-%d"),
            _format_dt(self.start_dt),
            _format_dt(end_dt),
            elapsed_seconds,
            round(elapsed_seconds / 60, 2),
            _format_duration(elapsed_seconds),
            APP_VERSION,
        ]
        _append_usage_record_async("使用记录", "使用记录", USAGE_HEADERS, row)
        print(f"本次使用时长: {_format_duration(elapsed_seconds)}")

    def _append_survey(self, profile: dict[str, str]) -> None:
        row = [
            _format_dt(_now()),
            profile.get("user_name", getpass.getuser()),
            profile.get("host_name", socket.gethostname()),
            profile.get("department", ""),
            profile.get("lm_group", ""),
            profile.get("pl_group", ""),
            profile.get("project_name", ""),
            APP_VERSION,
        ]
        _append_usage_record_async("用户问卷", "用户问卷", SURVEY_HEADERS, row)


class UsageSurveyDialog(QDialog):
    def __init__(self, parent: Any = None, profile: dict[str, str] | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("用户信息登记")
        self.setMinimumSize(500, 580)
        profile = profile or {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        intro = QLabel("首次使用前请补充以下信息，用于内部试用统计和需求跟踪。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        layout.addSpacing(4)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(16)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.user_edit = QLineEdit(profile.get("user_name", ""))
        self.user_edit.setPlaceholderText("非必填")
        self.department_combo = QComboBox()
        self.department_other_edit = QLineEdit()
        self.department_other_edit.setPlaceholderText("请输入部门")
        self.lm_group_combo = QComboBox()
        self.lm_group_other_edit = QLineEdit()
        self.lm_group_other_edit.setPlaceholderText("请输入LM大组")
        self.pl_group_combo = QComboBox()
        self.pl_group_other_edit = QLineEdit()
        self.pl_group_other_edit.setPlaceholderText("请输入PL小组")
        self.project_edit = QLineEdit(profile.get("project_name", ""))
        self.project_edit.setPlaceholderText("交付、技术项目均可，多个项目可用逗号分隔")

        for widget in (
            self.user_edit,
            self.department_combo,
            self.department_other_edit,
            self.lm_group_combo,
            self.lm_group_other_edit,
            self.pl_group_combo,
            self.pl_group_other_edit,
            self.project_edit,
        ):
            widget.setFixedHeight(32)

        form.addRow("用户姓名:", self.user_edit)
        form.addRow("部门:", self.department_combo)
        form.addRow("", self.department_other_edit)
        form.addRow("LM大组:", self.lm_group_combo)
        form.addRow("", self.lm_group_other_edit)
        form.addRow("PL小组:", self.pl_group_combo)
        form.addRow("", self.pl_group_other_edit)
        form.addRow("应用项目名:", self.project_edit)
        layout.addLayout(form, 1)

        self.department_combo.currentTextChanged.connect(self._on_department_changed)
        self.lm_group_combo.currentTextChanged.connect(self._on_lm_group_changed)
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
            "project_name": self.project_edit.text().strip(),
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

    def _lm_options(self) -> list[str]:
        department = self._current_value(
            self.department_combo, self.department_other_edit)
        if department == PRIMARY_DEPARTMENT:
            return LM_GROUP_OPTIONS
        return LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT

    def _pl_options(self) -> list[str]:
        lm_group = self._current_value(self.lm_group_combo, self.lm_group_other_edit)
        return PL_GROUP_OPTIONS_BY_LM.get(lm_group, PL_GROUP_OPTIONS_FOR_OTHER_LM)

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


def _load_profile() -> dict[str, str]:
    for path in _profile_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                profile = json.load(f)
            base = _base_profile()
            base.update({k: str(v) for k, v in profile.items()})
            return base
        except Exception as exc:
            print(f"提示：用户资料读取失败，已尝试下一个路径: {path}，错误: {exc}")
    return _base_profile()


def _save_profile(profile: dict[str, str]) -> None:
    failures: list[tuple[Path, str]] = []
    for path in _profile_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            print(f"用户资料已保存到本地: {path}")
            return
        except Exception as exc:
            failures.append((path, str(exc)))

    details = "; ".join(f"{path}: {error}" for path, error in failures)
    raise RuntimeError(details or "未配置用户资料本地保存路径")


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


def _profile_path() -> Path:
    paths = _profile_paths()
    if paths:
        return paths[0]
    return _app_base_dir() / "Public" / "usage_profile.json"


def _profile_paths() -> list[Path]:
    return configured_paths(PROFILE_PATHS_BY_PLATFORM, _app_base_dir())


def _append_usage_record_async(
    record_name: str, sheet_name: str, headers: list[str], row: list[Any]
) -> None:
    append_excel_row_async(
        record_name=record_name,
        sheet_name=sheet_name,
        headers=headers,
        row=row,
        local_paths=configured_paths(USAGE_LOCAL_EXCEL_PATHS_BY_PLATFORM, _app_base_dir()),
        developer_paths=configured_paths(
            USAGE_DEVELOPER_EXCEL_PATHS_BY_PLATFORM, _app_base_dir()
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
    from PyQt6.QtWidgets import QApplication

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
