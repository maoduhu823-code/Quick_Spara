"""
可复用的版本更新提醒模块。

复制到其他 PyQt app 时，修改本文件顶部配置区，并在 QApplication 创建后调用
check_version_update()。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.request import Request, urlopen


# ==============================
# 需要经常修改的配置区
# ==============================

APP_NAME = "Quick_Sparam"
APP_VERSION = "2026.03"

# 不同系统下的版本信息文件位置。会按顺序尝试，读到第一个有效 JSON 即停止。
VERSION_SOURCES_BY_PLATFORM = {
    "win32": [
        "Public/version.json",
        # 固定共享路径示例：需要时取消注释并改成你的公司共享路径。
        r"\\10.114.193.143\Public\version.json",
    ],
    "linux": [
        "/data/Storage_pisi/w00810255/Qs/Public/version.json",
    ],
    "default": [],
}

UPDATE_DIALOG_TITLE = "发现新版本"
UPDATE_DIALOG_TEXT = (
    "检测到 Quick_Sparam 新版本：{latest_version}\n"
    "当前版本：{current_version}\n\n"
    "请到共享目录获取新版程序。"
)

READ_TIMEOUT_SECONDS = 4


def check_version_update(parent: Any = None, show_dialog: bool = True) -> bool:
    """
    检查是否存在新版本。

    返回 True 表示检测到高于当前版本的新版本；False 表示未发现或版本文件不可用。
    """

    version_data = _try_load_version_data()
    if not version_data:
        return False

    latest_version = _first_text(version_data, "latest_version", "version")
    if not latest_version:
        return False

    if _compare_versions(latest_version, APP_VERSION) <= 0:
        return False

    if show_dialog:
        title = version_data.get("title") or UPDATE_DIALOG_TITLE
        text_template = version_data.get("message") or UPDATE_DIALOG_TEXT
        text = text_template.format(
            latest_version=latest_version,
            current_version=APP_VERSION,
        )
        notes = version_data.get("release_notes") or []
        if notes:
            text += "\n\n更新内容：\n" + "\n".join(f"- {note}" for note in notes)
        _show_information(parent, title, text)
    return True


def _try_load_version_data() -> dict[str, Any] | None:
    for source in _version_sources():
        try:
            text = _read_text(source)
            data = json.loads(text)
            if data.get("app") not in (None, APP_NAME):
                continue
            data["_version_source"] = source
            return data
        except Exception:
            continue
    return None


def _read_text(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = Request(source, headers={"Cache-Control": "no-cache"})
        with urlopen(request, timeout=READ_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8-sig")

    path = _resolve_file_source(source)
    with path.open("r", encoding="utf-8-sig") as f:
        return f.read()


def _resolve_file_source(source: str) -> Path:
    path = Path(os.path.expandvars(os.path.expanduser(source)))
    if path.is_absolute():
        return path

    candidates = [
        _app_base_dir() / path,
        Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _version_sources() -> list[str]:
    sources = _platform_value(VERSION_SOURCES_BY_PLATFORM)
    return [source for source in sources if source]


def _platform_value(mapping: dict[str, Any]) -> Any:
    if sys.platform in mapping:
        return mapping[sys.platform]
    if sys.platform.startswith("linux") and "linux" in mapping:
        return mapping["linux"]
    return mapping.get("default")


def _compare_versions(left: str, right: str) -> int:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    max_len = max(len(left_parts), len(right_parts))
    left_parts += [0] * (max_len - len(left_parts))
    right_parts += [0] * (max_len - len(right_parts))
    if left_parts > right_parts:
        return 1
    if left_parts < right_parts:
        return -1
    return 0


def _version_parts(value: str) -> list[int]:
    parts = [int(part) for part in re.findall(r"\d+", str(value))]
    return parts or [0]


def _first_text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return None


def _show_information(parent: Any, title: str, text: str) -> None:
    try:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(parent, title, text, QMessageBox.StandardButton.Ok)
    except Exception:
        print(f"{title}: {text}")
