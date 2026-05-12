"""
可复用的版本更新提醒模块。

复制到其他 PyQt app 时，修改本文件顶部配置区，并在 QApplication 创建后调用
check_version_update()。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import re
import sys
import threading
from typing import Any
from urllib.request import Request, urlopen

try:
    from .collection_config import APP_NAME, APP_VERSION
    from .path_config import VERSION_SOURCES_BY_PLATFORM
    from .notice_manager import ACCESS_UNAVAILABLE_MESSAGE, print_access_unavailable_once
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from QS_runtime_services.collection_config import APP_NAME, APP_VERSION
    from QS_runtime_services.path_config import VERSION_SOURCES_BY_PLATFORM
    from QS_runtime_services.notice_manager import (
        ACCESS_UNAVAILABLE_MESSAGE,
        print_access_unavailable_once,
    )


# ==============================
# 需要经常修改的配置区
# ==============================

# 启动时和“版本信息”按钮输出的版本说明。
VERSION_INFO_TITLE = "B2026版主要更新内容如下："
VERSION_INFO_ITEMS = [
    "---功能增加",
    "【版本管理】   新增版本检查功能，有新版本发布自动提醒更新",
    "【文件列表】   新增完整路径/文件名显示模式切换，长路径文件可简化显示",
    "【缓存管理】   新增S/Y/Z参数统一懒加载缓存、文件指纹校验和缓存调试开关",
    "【数据复用】   频域分析、时域分析、纹波拟合和端口合并统一复用主窗口缓存数据",
    "---交互体验",
    "【文件列表】   显示文件名时仍保留真实文件路径，避免后续分析找不到原始文件",
    "【频域分析】   修复文件名显示模式下指定线号、最差bit和XTSum等分析的数据访问问题",
    "【端口处理】   合并了多个端口处理的功能，其中新增了<端口合并>功能",
]

# 版本信息文件路径统一在 QS_runtime_services/path_config.py 中配置。

UPDATE_DIALOG_TITLE = "发现新版本"
UPDATE_DIALOG_TEXT = (
    "检测到 Quick_Sparam 新版本：{latest_version}\n"
    "当前版本：{current_version}\n\n"
    "请到共享目录获取新版程序。"
)
VERSION_SOURCE_UNAVAILABLE_MESSAGE = ACCESS_UNAVAILABLE_MESSAGE

VERSION_CHECK_TIMEOUT_SECONDS = 2
READ_TIMEOUT_SECONDS = VERSION_CHECK_TIMEOUT_SECONDS

_VERSION_CHECK_TIMEOUT = object()


def get_version_info_lines(current_version: str | None = None) -> list[str]:
    version = current_version or APP_VERSION
    return [
        VERSION_INFO_TITLE,
        *VERSION_INFO_ITEMS,
        "",
        f"版本持续迭代中，当前版本号为{version}",
    ]


def print_version_info(
    current_version: str | None = None,
    printer: Any = print,
) -> None:
    for line in get_version_info_lines(current_version):
        printer(line)


def check_version_update(
    parent: Any = None,
    show_dialog: bool = True,
    timeout_seconds: float | None = VERSION_CHECK_TIMEOUT_SECONDS,
) -> bool:
    """
    检查是否存在新版本。

    返回 True 表示检测到高于当前版本的新版本；False 表示未发现或版本文件不可用。
    """

    version_data = _try_load_version_data_with_timeout(timeout_seconds)
    return _handle_version_data(version_data, parent, show_dialog)


def check_version_update_async(
    parent: Any = None,
    show_dialog: bool = True,
    timeout_seconds: float = VERSION_CHECK_TIMEOUT_SECONDS,
) -> None:
    """后台检查新版本，避免共享路径访问拖慢主界面启动。"""

    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication
    except Exception:
        check_version_update(parent, show_dialog, timeout_seconds)
        return

    app = QApplication.instance()
    if app is None:
        check_version_update(parent, show_dialog, timeout_seconds)
        return

    result_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
    state = {"done": False}

    def worker():
        try:
            result = _try_load_version_data()
        except Exception:
            result = None
        try:
            result_queue.put_nowait(result)
        except queue.Full:
            pass

    thread = threading.Thread(target=worker, name="version-update-check", daemon=True)
    owner = parent or app
    poll_timer = QTimer(owner)
    timeout_timer = QTimer(owner)
    refs = getattr(owner, "_version_check_refs", None)
    if refs is None:
        refs = []
        setattr(owner, "_version_check_refs", refs)
    token = {
        "thread": thread,
        "poll_timer": poll_timer,
        "timeout_timer": timeout_timer,
        "result_queue": result_queue,
    }
    refs.append(token)

    def cleanup():
        poll_timer.stop()
        timeout_timer.stop()
        try:
            refs.remove(token)
        except ValueError:
            pass

    def finish(version_data: Any):
        if state["done"]:
            return
        state["done"] = True
        _handle_version_data(version_data, parent, show_dialog)
        cleanup()

    def poll_result():
        if state["done"]:
            cleanup()
            return
        try:
            version_data = result_queue.get_nowait()
        except queue.Empty:
            return
        finish(version_data)

    def timeout():
        finish(_VERSION_CHECK_TIMEOUT)

    poll_timer.setInterval(100)
    poll_timer.timeout.connect(poll_result)
    timeout_timer.setSingleShot(True)
    timeout_timer.timeout.connect(timeout)

    thread.start()
    poll_timer.start()
    timeout_timer.start(max(1, int(timeout_seconds * 1000)))


def _handle_version_data(version_data: Any, parent: Any = None, show_dialog: bool = True) -> bool:
    if not version_data:
        print_access_unavailable_once()
        return False

    if version_data is _VERSION_CHECK_TIMEOUT:
        print_access_unavailable_once()
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
        location = _first_text(
            version_data,
            "download_url", "download_path", "update_url", "update_path", "path",
        )
        _show_update_dialog(parent, title, text, location)
    return True


def _try_load_version_data_with_timeout(timeout_seconds: float | None) -> Any:
    if timeout_seconds is None or timeout_seconds <= 0:
        return _try_load_version_data()

    result_queue: queue.Queue[Any] = queue.Queue(maxsize=1)

    def worker():
        try:
            result = _try_load_version_data()
        except Exception:
            result = None
        try:
            result_queue.put_nowait(result)
        except queue.Full:
            pass

    thread = threading.Thread(target=worker, name="version-update-check", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        return _VERSION_CHECK_TIMEOUT
    try:
        return result_queue.get_nowait()
    except queue.Empty:
        return None


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
    return Path(__file__).resolve().parent.parent


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


def _show_update_dialog(
    parent: Any,
    title: str,
    text: str,
    location: str | None = None,
) -> None:
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QApplication, QMessageBox

        if location:
            text = f"{text}\n\n获取路径（文件资源管理器中打开）：\n{location}"

        message_box = QMessageBox(parent)
        message_box.setIcon(QMessageBox.Icon.Information)
        message_box.setWindowTitle(title)
        message_box.setText(text)
        message_box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        copy_button = None
        if location:
            copy_button = message_box.addButton(
                "复制路径", QMessageBox.ButtonRole.ActionRole
            )
        message_box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        message_box.exec()
        if copy_button and message_box.clickedButton() == copy_button:
            QApplication.clipboard().setText(location)
    except Exception:
        print(f"{title}: {text}")
        if location:
            print(f"获取路径: {location}")
