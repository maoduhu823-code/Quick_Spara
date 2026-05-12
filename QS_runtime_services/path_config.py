"""
QS_runtime_services 统一路径配置。

按环境约定：
- Windows 公司内部使用：只读共享目录用于版本/授权文件，读写共享目录用于问卷/反馈收集。
- Windows 本机开发：使用程序目录下的 Public 文件夹。
- Linux：使用指定服务器目录。
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath


WINDOWS_COMPANY_READONLY_DIR = r"\\10.114.193.143\Public"
WINDOWS_COMPANY_READWRITE_DIR = r"\\10.114.193.143\Public_userdate_collect"
WINDOWS_LOCAL_PUBLIC_DIR = r".\Public"
LINUX_DATA_DIR = "/data/hs_5023_public/Quick_Sparam/data_feedback"


def _win_path(base_dir: str, *parts: str) -> str:
    return str(PureWindowsPath(base_dir, *parts))


def _linux_path(*parts: str) -> str:
    return str(PurePosixPath(LINUX_DATA_DIR, *parts))


def windows_readonly_file(filename: str) -> str:
    """Windows 公司只读共享目录中的文件。"""
    return _win_path(WINDOWS_COMPANY_READONLY_DIR, filename)


def windows_readwrite_file(filename: str) -> str:
    """Windows 公司读写共享目录中的文件。"""
    return _win_path(WINDOWS_COMPANY_READWRITE_DIR, filename)


def windows_local_public_file(filename: str) -> str:
    """Windows 本机开发 Public 目录中的文件。"""
    return _win_path(WINDOWS_LOCAL_PUBLIC_DIR, filename)


def windows_local_feedback_path(*parts: str) -> str:
    """Windows 本机开发 Public/data_feedback 目录中的路径。"""
    return _win_path(WINDOWS_LOCAL_PUBLIC_DIR, "data_feedback", *parts)


def windows_readwrite_feedback_path(*parts: str) -> str:
    """Windows 公司读写共享目录 data_feedback 下的路径。"""
    return _win_path(WINDOWS_COMPANY_READWRITE_DIR, "data_feedback", *parts)


def linux_data_file(filename: str) -> str:
    """Linux 服务器数据目录中的文件。"""
    return _linux_path(filename)


def linux_feedback_path(*parts: str) -> str:
    """Linux 服务器 data_feedback 目录中的路径。"""
    return _linux_path(*parts)


LICENSE_SOURCES_BY_PLATFORM = {
    "win32": [
        windows_readonly_file("license.json"),
        windows_local_public_file("license.json"),
    ],
    "linux": [
        linux_data_file("license.json"),
    ],
    "default": [
        windows_local_public_file("license.json"),
    ],
}

VERSION_SOURCES_BY_PLATFORM = {
    "win32": [
        windows_readonly_file("version.json"),
        windows_local_public_file("version.json"),
    ],
    "linux": [
        linux_data_file("version.json"),
    ],
    "default": [
        windows_local_public_file("version.json"),
    ],
}

PROFILE_PATHS_BY_PLATFORM = {
    "win32": [
        windows_local_public_file("usage_profile.json"),
    ],
    "linux": [
        linux_data_file("usage_profile.json"),
    ],
    "default": [
        windows_local_public_file("usage_profile.json"),
    ],
}

USAGE_LOCAL_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_local_feedback_path("Quick_Sparam_usage_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_usage_summary.xlsx"),
    ],
    "default": [
        windows_local_feedback_path("Quick_Sparam_usage_summary.xlsx"),
    ],
}

USER_DATA_LOCAL_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_local_feedback_path("Quick_Sparam_user_data_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_user_data_summary.xlsx"),
    ],
    "default": [
        windows_local_feedback_path("Quick_Sparam_user_data_summary.xlsx"),
    ],
}

USAGE_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_readwrite_feedback_path("Quick_Sparam_usage_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_usage_summary.xlsx"),
    ],
    "default": [],
}

USER_DATA_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_readwrite_feedback_path("Quick_Sparam_user_data_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_user_data_summary.xlsx"),
    ],
    "default": [],
}

FEEDBACK_LOCAL_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_local_feedback_path("Quick_Sparam_feedback_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_feedback_summary.xlsx"),
    ],
    "default": [
        windows_local_feedback_path("Quick_Sparam_feedback_summary.xlsx"),
    ],
}

FEEDBACK_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM = {
    "win32": [
        windows_readwrite_feedback_path("Quick_Sparam_feedback_summary.xlsx"),
    ],
    "linux": [
        linux_feedback_path("Quick_Sparam_feedback_summary.xlsx"),
    ],
    "default": [],
}

LOCAL_RECORD_INBOX_DIRS_BY_PLATFORM = {
    "win32": [
        windows_local_feedback_path("inbox"),
    ],
    "linux": [],
    "default": [
        windows_local_feedback_path("inbox"),
    ],
}

DEVELOPER_RECORD_INBOX_DIRS_BY_PLATFORM = {
    "win32": [
        windows_readwrite_feedback_path("inbox"),
    ],
    "linux": [
        linux_feedback_path("inbox"),
    ],
    "default": [],
}

# 兼容旧名称：当前应用不再直接写 Excel，这些路径用于汇总程序输出 summary。
USAGE_LOCAL_EXCEL_PATHS_BY_PLATFORM = USAGE_LOCAL_SUMMARY_PATHS_BY_PLATFORM
USAGE_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = USAGE_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
USER_DATA_LOCAL_EXCEL_PATHS_BY_PLATFORM = USER_DATA_LOCAL_SUMMARY_PATHS_BY_PLATFORM
USER_DATA_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = USER_DATA_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
FEEDBACK_LOCAL_EXCEL_PATHS_BY_PLATFORM = FEEDBACK_LOCAL_SUMMARY_PATHS_BY_PLATFORM
FEEDBACK_DEVELOPER_EXCEL_PATHS_BY_PLATFORM = FEEDBACK_DEVELOPER_SUMMARY_PATHS_BY_PLATFORM
