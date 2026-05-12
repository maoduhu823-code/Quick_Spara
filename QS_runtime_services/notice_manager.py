"""运行期提示去重工具。"""

from __future__ import annotations

from threading import Lock


ACCESS_UNAVAILABLE_MESSAGE = "无法访问版本更新地址，请联系管理员w00810255添加路径访问权限"

_printed_notice_keys: set[str] = set()
_notice_lock = Lock()


def print_notice_once(key: str, message: str) -> None:
    """同一 Python 进程内，同一个 key 只输出一次。"""
    with _notice_lock:
        if key in _printed_notice_keys:
            return
        _printed_notice_keys.add(key)
    print(message)


def print_access_unavailable_once() -> None:
    print_notice_once("access_unavailable", ACCESS_UNAVAILABLE_MESSAGE)
