"""
QS_runtime_services 统一路径配置。

两种运行模式：
- **本机开发模式**：当前 hostname 在 DEV_HOSTNAMES 白名单内，或 Quick_Sparam_B.py
  以 --dev 启动并调用 force_local_mode()。一切都落在程序基准目录旁的 ./Public/，
  零网络。
- **分发模式**：其他所有 hostname。按平台分支：
  * 读路径（只读、共享）= version.json / license.json
  * 写路径（读写、共享）= usage_profile.json / data_feedback/inbox/ / data_feedback/*.xlsx
  * 共享盘不可达时落到本机 ./Public/ 兜底（A 报错 + B 兜底）。

路径解析全部在函数中按调用时机判断，所以 force_local_mode() 必须在被消费的模块
import 之前调用（Quick_Sparam_B.py 已经满足这个顺序）。
"""

from __future__ import annotations

import socket
import sys
from pathlib import PurePosixPath, PureWindowsPath


# -------------------------- 运行模式 --------------------------

# 本机开发机白名单（大写比对 → 忽略大小写）。
# Davidworld = 个人开发机；W00810255 / W00810255-NFWP = 出差/借用的公司机。
DEV_HOSTNAMES = {"DAVIDWORLD", "W00810255", "W00810255-NFWP"}

_FORCE_LOCAL_MODE = False


def force_local_mode(enabled: bool = True) -> None:
    """命令行 --dev 启动时强制进入本机模式（即使 hostname 不在白名单）。"""
    global _FORCE_LOCAL_MODE
    _FORCE_LOCAL_MODE = bool(enabled)


def is_local_mode() -> bool:
    if _FORCE_LOCAL_MODE:
        return True
    try:
        return socket.gethostname().upper() in DEV_HOSTNAMES
    except Exception:
        return False


# -------------------------- 基础常量 --------------------------

# Windows 共享目录
WINDOWS_READONLY_DIR = r"\\10.114.193.143\Public"          # 读路径：version / license
WINDOWS_READWRITE_DIR = r"\\10.114.193.143\data_feedback"  # 写路径：profile / inbox / summary

# Linux 共享目录（同一基目录下分子目录区分读写）
LINUX_READONLY_DIR = "/data/hs_5023_public/Quick_Sparam/Public"
LINUX_READWRITE_DIR = "/data/hs_5023_public/Quick_Sparam/data_feedback"

# 本机相对路径（解析时由调用方与 _app_base_dir 拼接）
LOCAL_PUBLIC_DIR_WIN = r".\Public"
LOCAL_PUBLIC_DIR_POSIX = "./Public"


def _win(base: str, *parts: str) -> str:
    return str(PureWindowsPath(base, *parts))


def _posix(base: str, *parts: str) -> str:
    return str(PurePosixPath(base, *parts))


def _local_public_win(*parts: str) -> str:
    return _win(LOCAL_PUBLIC_DIR_WIN, *parts)


def _local_public_posix(*parts: str) -> str:
    return _posix(LOCAL_PUBLIC_DIR_POSIX, *parts)


def _local_public(*parts: str) -> str:
    """本机 ./Public/ 下的路径，按当前平台选风格。"""
    if sys.platform.startswith("linux"):
        return _local_public_posix(*parts)
    return _local_public_win(*parts)


def _local_feedback(*parts: str) -> str:
    return _local_public("data_feedback", *parts)


# -------------------------- 读路径（version / license） --------------------------


def _readonly_file(filename: str) -> str:
    if sys.platform == "win32":
        return _win(WINDOWS_READONLY_DIR, filename)
    if sys.platform.startswith("linux"):
        return _posix(LINUX_READONLY_DIR, filename)
    return _local_public(filename)


def license_sources() -> list[str]:
    """授权文件读取顺序：共享 → 本机兜底。本机模式只读本机。"""
    if is_local_mode():
        return [_local_public("license.json")]
    return [_readonly_file("license.json"), _local_public("license.json")]


def version_sources() -> list[str]:
    """版本文件读取顺序：共享 → 本机兜底。本机模式只读本机。"""
    if is_local_mode():
        return [_local_public("version.json")]
    return [_readonly_file("version.json"), _local_public("version.json")]


# -------------------------- 写路径（profile / inbox / summary） --------------------------


def _readwrite(*parts: str) -> str:
    if sys.platform == "win32":
        return _win(WINDOWS_READWRITE_DIR, *parts)
    if sys.platform.startswith("linux"):
        return _posix(LINUX_READWRITE_DIR, *parts)
    return _local_feedback(*parts)


def profile_local_path() -> str:
    """本机 usage_profile.json：本机模式唯一存档；分发模式作为本机兜底+UI 入口。"""
    return _local_public("usage_profile.json")


def profile_remote_path() -> str | None:
    """共享 usage_profile.json：本机模式 = None；分发模式下用来双写。"""
    if is_local_mode():
        return None
    return _readwrite("usage_profile.json")


def profile_paths() -> list[str]:
    """读取顺序：本机优先（兜底），共享次之。也用于双写时的目标集合。"""
    paths = [profile_local_path()]
    remote = profile_remote_path()
    if remote:
        paths.append(remote)
    return paths


def _summary_filenames() -> dict[str, str]:
    return {
        "usage": "Quick_Sparam_usage_summary.xlsx",
        "user_data": "Quick_Sparam_user_data_summary.xlsx",
        "feedback": "Quick_Sparam_feedback_summary.xlsx",
    }


def _summary_paths(kind: str, *, primary: bool) -> list[str]:
    """summary Excel 路径。primary=True 返回主路径（本机模式=本机/分发模式=共享）；
    primary=False 返回兜底路径（仅分发模式下为本机；本机模式返回空）。"""
    filename = _summary_filenames()[kind]
    if is_local_mode():
        return [_local_feedback(filename)] if primary else []
    if primary:
        return [_readwrite(filename)]
    return [_local_feedback(filename)]


def usage_summary_paths_primary() -> list[str]:
    return _summary_paths("usage", primary=True)


def usage_summary_paths_fallback() -> list[str]:
    return _summary_paths("usage", primary=False)


def user_data_summary_paths_primary() -> list[str]:
    return _summary_paths("user_data", primary=True)


def user_data_summary_paths_fallback() -> list[str]:
    return _summary_paths("user_data", primary=False)


def feedback_summary_paths_primary() -> list[str]:
    return _summary_paths("feedback", primary=True)


def feedback_summary_paths_fallback() -> list[str]:
    return _summary_paths("feedback", primary=False)


def inbox_dirs_primary() -> list[str]:
    """inbox 主目标：本机模式=本机；分发模式=共享。"""
    if is_local_mode():
        return [_local_feedback("inbox")]
    return [_readwrite("inbox")]


def inbox_dirs_fallback() -> list[str]:
    """inbox 兜底：本机模式无；分发模式=本机 ./Public/data_feedback/inbox/。"""
    if is_local_mode():
        return []
    return [_local_feedback("inbox")]


# -------------------------- 历史名称兼容层 --------------------------
# 现有 record_writer.configured_paths 接收 dict[platform → list] 形式。为了不动调用
# 现场，这里用一个轻量包装把"主+兜底"两个函数组合成与旧 mapping 等价的 dict。
# 注意：本机模式下 developer_* 返回空列表，等价于"不写共享"。


def _as_mapping(primary: list[str], fallback: list[str] | None = None) -> dict[str, list[str]]:
    combined = list(primary)
    if fallback:
        for path in fallback:
            if path not in combined:
                combined.append(path)
    return {
        "win32": combined,
        "linux": combined,
        "default": combined,
    }


def _developer_mapping(primary: list[str]) -> dict[str, list[str]]:
    return {
        "win32": list(primary),
        "linux": list(primary),
        "default": [],
    }


class _LazyMapping:
    """像 dict 一样被 `_platform_value` / `configured_paths` 消费，但每次取值时
    重新计算 → 跟随 force_local_mode() 的最新状态。"""

    def __init__(self, resolver):
        self._resolver = resolver

    def __getitem__(self, key):
        return self._resolver()[key]

    def get(self, key, default=None):
        return self._resolver().get(key, default)

    def __contains__(self, key):
        return key in self._resolver()

    def __iter__(self):
        return iter(self._resolver())

    def keys(self):
        return self._resolver().keys()

    def values(self):
        return self._resolver().values()

    def items(self):
        return self._resolver().items()


LICENSE_SOURCES_BY_PLATFORM = _LazyMapping(lambda: _as_mapping(license_sources()))
VERSION_SOURCES_BY_PLATFORM = _LazyMapping(lambda: _as_mapping(version_sources()))
PROFILE_PATHS_BY_PLATFORM = _LazyMapping(lambda: _as_mapping(profile_paths()))

USAGE_LOCAL_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _as_mapping(usage_summary_paths_fallback() or usage_summary_paths_primary())
)
USER_DATA_LOCAL_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _as_mapping(user_data_summary_paths_fallback() or user_data_summary_paths_primary())
)
FEEDBACK_LOCAL_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _as_mapping(feedback_summary_paths_fallback() or feedback_summary_paths_primary())
)

USAGE_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _developer_mapping(usage_summary_paths_primary() if not is_local_mode() else [])
)
USER_DATA_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _developer_mapping(user_data_summary_paths_primary() if not is_local_mode() else [])
)
FEEDBACK_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = _LazyMapping(
    lambda: _developer_mapping(feedback_summary_paths_primary() if not is_local_mode() else [])
)

LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM = _LazyMapping(
    lambda: _as_mapping(inbox_dirs_fallback() or inbox_dirs_primary())
)
DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM = _LazyMapping(
    lambda: _developer_mapping(inbox_dirs_primary() if not is_local_mode() else [])
)

# 旧式 EXCEL_PATHS 别名（曾经用于直接写 Excel，现仅向后兼容）
USAGE_LOCAL_EXCEL_PATHS_BY_PLATFORM = USAGE_LOCAL_SUMMARY_PATHS_BY_PLATFORM
USAGE_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = USAGE_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
USER_DATA_LOCAL_EXCEL_PATHS_BY_PLATFORM = USER_DATA_LOCAL_SUMMARY_PATHS_BY_PLATFORM
USER_DATA_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = USER_DATA_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
FEEDBACK_LOCAL_EXCEL_PATHS_BY_PLATFORM = FEEDBACK_LOCAL_SUMMARY_PATHS_BY_PLATFORM
FEEDBACK_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = FEEDBACK_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
