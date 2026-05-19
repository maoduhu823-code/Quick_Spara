"""
可复用的绝对日期试用/限用检查模块。

复制到其他 PyQt app 时，只需要：
1. 修改本文件顶部的配置区；
2. 在入口 QApplication 创建后、主窗口创建前调用 check_trial_permission()。
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
import sys
import threading
import time as monotonic_time
from datetime import datetime, time, timedelta, timezone
from typing import Any
from urllib.request import Request, urlopen

try:
    from .path_config import LICENSE_SOURCES_BY_PLATFORM
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from QS_runtime_services.path_config import LICENSE_SOURCES_BY_PLATFORM


# ==============================
# 需要经常修改的配置区
# ==============================

# 复制到其他软件时，先改这里。它会影响本地缓存目录名和授权文件里的 app 校验。
APP_NAME = "Quick_Sparam"

# 默认绝对到期日：共享授权文件不可访问时，软件会继续使用本地缓存中的该日期。
# 支持 "2026-08-01"、"2026.08.01"、"2026-08-01 23:59:59"、
# "2026-08-01T23:59:59+08:00" 等格式。
DEFAULT_EXPIRE_AT = "2026-08-01 23:59:59"

# 授权文件路径统一在 QS_runtime_services/path_config.py 中配置。

# 本地状态文件存放目录。设为 None 时使用系统默认用户目录。
# Windows 默认：%APPDATA%\Quick_Sparam\trial_state.json
# Linux 默认：~/.config/Quick_Sparam/trial_state.json
LOCAL_STATE_DIR_BY_PLATFORM = {
    "win32": None,
    "linux": None,
    "darwin": None,
    "default": None,
}

# 过期弹窗文本。
EXPIRED_DIALOG_TITLE = "试用期已结束"
EXPIRED_DIALOG_TEXT = (
    "当前版本试用期已结束。\n\n"
    "请连接公司共享授权路径获取延期信息，或联系管理员更新使用权限。"
)

# 共享授权文件明确关闭软件时的弹窗文本。
DISABLED_DIALOG_TITLE = "使用权限已关闭"
DISABLED_DIALOG_TEXT = "当前版本已被管理员关闭使用权限，请联系管理员。"

# 检测到本机时间明显回拨时的弹窗文本。
CLOCK_ROLLBACK_DIALOG_TITLE = "系统时间异常"
CLOCK_ROLLBACK_DIALOG_TEXT = "检测到系统时间早于上次运行时间，请校准系统时间后重新打开软件。"

# 授权源读取超时时间，单位秒；共享文件路径也受该值保护，避免拖慢启动。
LICENSE_CHECK_TIMEOUT_SECONDS = 2
READ_TIMEOUT_SECONDS = LICENSE_CHECK_TIMEOUT_SECONDS

# 允许本机时间比上次运行时间提前多少分钟，超过则认为系统时间异常。
CLOCK_ROLLBACK_TOLERANCE_MINUTES = 30

# 默认为 False：共享授权只能把日期往后延，不会缩短本地已缓存的截止日期。
# 如需管理员通过共享文件提前收回全局日期，可以改为 True；也可以用 enabled=false 立即关闭。
ALLOW_LICENSE_TO_SHORTEN_EXPIRE_AT = False


# ==============================
# 对外入口
# ==============================

def check_trial_permission(parent: Any = None, show_dialog: bool = True) -> bool:
    """
    检查当前软件是否允许启动。

    parent:
        PyQt 窗口对象；入口处主窗口尚未创建时可以传 None。
    show_dialog:
        False 时只返回 True/False，不弹窗。
    """

    now_dt = _now()
    state_path = get_state_path()
    state = _load_or_create_state(state_path, now_dt)

    if _is_clock_rollback(state, now_dt):
        state["last_denied_reason"] = "clock_rollback"
        _save_state(state_path, state)
        if show_dialog:
            _show_critical(parent, CLOCK_ROLLBACK_DIALOG_TITLE, CLOCK_ROLLBACK_DIALOG_TEXT)
        return False

    license_result = _try_load_shared_license()
    if license_result["data"]:
        decision = _apply_license_data(state, license_result["data"], license_result["source"], now_dt)
        _save_state(state_path, state)
        if decision["denied"]:
            title = decision["title"] or DISABLED_DIALOG_TITLE
            text = decision["text"] or DISABLED_DIALOG_TEXT
            if show_dialog:
                _show_critical(parent, title, text)
            return False
    else:
        state["last_license_check_at"] = _format_dt(now_dt)
        state["last_license_error"] = license_result["error"]
        _save_state(state_path, state)

    expire_at = _parse_datetime(state.get("expire_at") or DEFAULT_EXPIRE_AT)
    if now_dt > expire_at:
        state["last_run_at"] = _format_dt(now_dt)
        state["last_denied_reason"] = "expired"
        _save_state(state_path, state)
        if show_dialog:
            _show_critical(parent, EXPIRED_DIALOG_TITLE, _expired_text(expire_at, state))
        return False

    state["last_run_at"] = _format_dt(now_dt)
    state["last_denied_reason"] = None
    _save_state(state_path, state)
    return True


def get_state_path() -> Path:
    """返回本地 trial_state.json 的路径，便于排查和复用。"""

    configured_dir = _platform_value(LOCAL_STATE_DIR_BY_PLATFORM)
    if configured_dir:
        state_dir = Path(os.path.expandvars(os.path.expanduser(configured_dir)))
    elif sys.platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        state_dir = Path(appdata) / APP_NAME
    elif sys.platform == "darwin":
        state_dir = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        state_dir = Path.home() / ".config" / APP_NAME
    return state_dir / "trial_state.json"


def current_identity() -> dict[str, str]:
    """返回当前用户/设备标识。授权文件可使用 user、host、user_hash 或 device_id_hash 匹配。"""

    user = getpass.getuser()
    host = socket.gethostname()
    platform_name = sys.platform
    device_seed = f"{platform_name}|{user}|{host}|{APP_NAME}"
    return {
        "user": user,
        "user_lower": user.casefold(),
        "host": host,
        "host_lower": host.casefold(),
        "user_hash": _sha256(user.casefold()),
        "device_id_hash": _sha256(device_seed.casefold()),
    }


# ==============================
# 内部实现
# ==============================

def _load_or_create_state(state_path: Path, now_dt: datetime) -> dict[str, Any]:
    identity = current_identity()
    if state_path.exists():
        try:
            with state_path.open("r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            backup_path = state_path.with_suffix(".broken.json")
            try:
                state_path.replace(backup_path)
            except Exception:
                pass
            state = {}
    else:
        state = {}

    default_expire = _format_dt(_parse_datetime(DEFAULT_EXPIRE_AT))
    if not state:
        state = {
            "app": APP_NAME,
            "created_at": _format_dt(now_dt),
            "expire_at": default_expire,
            "last_run_at": None,
            "last_license_update_at": None,
            "last_license_source": None,
            "last_license_error": None,
            "user": identity["user"],
            "host": identity["host"],
            "user_hash": identity["user_hash"],
            "device_id_hash": identity["device_id_hash"],
        }
    else:
        state.setdefault("app", APP_NAME)
        state.setdefault("created_at", _format_dt(now_dt))
        state.setdefault("expire_at", default_expire)
        state.setdefault("user", identity["user"])
        state.setdefault("host", identity["host"])
        state.setdefault("user_hash", identity["user_hash"])
        state.setdefault("device_id_hash", identity["device_id_hash"])

    _save_state(state_path, state)
    return state


def _save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _try_load_shared_license() -> dict[str, Any]:
    errors = []
    deadline = monotonic_time.monotonic() + LICENSE_CHECK_TIMEOUT_SECONDS
    for source in _license_sources():
        try:
            remaining = deadline - monotonic_time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"授权源检查总超时（>{LICENSE_CHECK_TIMEOUT_SECONDS:.1f}s）")
            text = _read_text_with_timeout(source, remaining)
            data = json.loads(text)
            if data.get("app") not in (None, APP_NAME):
                errors.append(f"{source}: app 不匹配")
                continue
            return {"source": source, "data": data, "error": None}
        except Exception as exc:
            errors.append(f"{source}: {exc}")
    return {"source": None, "data": None, "error": " | ".join(errors) if errors else None}


def _read_text_with_timeout(source: str, timeout_seconds: float | None) -> str:
    if timeout_seconds is None or timeout_seconds <= 0:
        return _read_text(source)

    result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def worker():
        try:
            result_queue.put_nowait((True, _read_text(source)))
        except Exception as exc:
            try:
                result_queue.put_nowait((False, exc))
            except queue.Full:
                pass

    thread = threading.Thread(target=worker, name="license-source-read", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"读取授权源超时（>{timeout_seconds:.1f}s）")

    try:
        ok, value = result_queue.get_nowait()
    except queue.Empty:
        raise TimeoutError("读取授权源未返回结果")
    if ok:
        return value
    raise value


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


def _apply_license_data(
    state: dict[str, Any],
    data: dict[str, Any],
    source: str | None,
    now_dt: datetime,
) -> dict[str, Any]:
    if data.get("global_enabled", True) is False:
        state["last_denied_reason"] = "global_disabled"
        return {
            "denied": True,
            "title": data.get("disabled_title") or DISABLED_DIALOG_TITLE,
            "text": data.get("disabled_text") or data.get("message") or DISABLED_DIALOG_TEXT,
        }

    identity = current_identity()
    matched_entry = _find_matching_user_entry(data.get("users") or [], identity)
    if matched_entry and matched_entry.get("enabled", True) is False:
        state["last_denied_reason"] = "user_disabled"
        return {
            "denied": True,
            "title": matched_entry.get("disabled_title") or DISABLED_DIALOG_TITLE,
            "text": matched_entry.get("disabled_text") or matched_entry.get("message") or DISABLED_DIALOG_TEXT,
        }

    if data.get("require_user_match") and data.get("users") and not matched_entry:
        state["last_denied_reason"] = "user_not_allowed"
        return {
            "denied": True,
            "title": data.get("disabled_title") or DISABLED_DIALOG_TITLE,
            "text": data.get("disabled_text") or "当前用户不在授权名单中，请联系管理员。",
        }

    expire_text = None
    profile = {}
    if matched_entry:
        expire_text = _first_text(matched_entry, "expire_at", "expires_at", "valid_until")
        profile = {
            "license_user": matched_entry.get("user"),
            "license_group": matched_entry.get("group"),
            "license_project": matched_entry.get("project"),
        }
    if not expire_text:
        expire_text = _first_text(data, "default_expire_at", "expire_at", "expires_at", "valid_until")

    if expire_text:
        new_expire_at = _parse_datetime(expire_text)
        old_expire_at = _parse_datetime(state.get("expire_at") or DEFAULT_EXPIRE_AT)
        if ALLOW_LICENSE_TO_SHORTEN_EXPIRE_AT or new_expire_at > old_expire_at:
            state["expire_at"] = _format_dt(new_expire_at)
            state["last_license_update_at"] = _format_dt(now_dt)
            state["last_license_source"] = source
            state["last_license_message"] = data.get("message")
            for key, value in profile.items():
                if value:
                    state[key] = value

    state["last_license_check_at"] = _format_dt(now_dt)
    state["last_license_error"] = None
    return {"denied": False, "title": None, "text": None}


def _find_matching_user_entry(
    entries: list[dict[str, Any]],
    identity: dict[str, str],
) -> dict[str, Any] | None:
    for entry in entries:
        user = str(entry.get("user", "")).casefold()
        host = str(entry.get("host", "")).casefold()
        if user and user == identity["user_lower"]:
            return entry
        if host and host == identity["host_lower"]:
            return entry
        if entry.get("user_hash") and entry["user_hash"] == identity["user_hash"]:
            return entry
        if entry.get("device_id_hash") and entry["device_id_hash"] == identity["device_id_hash"]:
            return entry
    return None


def _license_sources() -> list[str]:
    sources = _platform_value(LICENSE_SOURCES_BY_PLATFORM)
    return [source for source in sources if source]


def _platform_value(mapping: dict[str, Any]) -> Any:
    if sys.platform in mapping:
        return mapping[sys.platform]
    if sys.platform.startswith("linux") and "linux" in mapping:
        return mapping["linux"]
    return mapping.get("default")


def _is_clock_rollback(state: dict[str, Any], now_dt: datetime) -> bool:
    last_run_at = state.get("last_run_at")
    if not last_run_at:
        return False
    try:
        last_dt = _parse_datetime(last_run_at)
    except ValueError:
        return False
    tolerance = timedelta(minutes=CLOCK_ROLLBACK_TOLERANCE_MINUTES)
    return now_dt + tolerance < last_dt


def _expired_text(expire_at: datetime, state: dict[str, Any]) -> str:
    return (
        f"{EXPIRED_DIALOG_TEXT}\n\n"
        f"当前本地授权截止日期：{_format_dt(expire_at)}\n"
        f"本地授权缓存：{get_state_path()}"
    )


def _show_critical(parent: Any, title: str, text: str) -> None:
    try:
        from qtpy.QtWidgets import QMessageBox

        QMessageBox.critical(parent, title, text, QMessageBox.StandardButton.Ok)
    except Exception:
        print(f"{title}: {text}")


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("日期为空")
        normalized = text.replace("Z", "+00:00")
        date_only = len(normalized) == 10 and normalized[4] in "-./" and normalized[7] in "-./"
        if date_only:
            normalized = normalized.replace(".", "-").replace("/", "-")
            dt = datetime.combine(datetime.fromisoformat(normalized).date(), time(23, 59, 59))
        else:
            normalized = normalized.replace(".", "-", 2)
            dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_local_tz())
    return dt.astimezone(_local_tz())


def _format_dt(dt: datetime) -> str:
    return dt.astimezone(_local_tz()).isoformat(timespec="seconds")


def _now() -> datetime:
    return datetime.now(_local_tz())


def _local_tz() -> timezone:
    return datetime.now().astimezone().tzinfo or timezone(timedelta(hours=8))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _first_text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return None
