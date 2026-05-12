"""
信息收集功能的极简调用入口。

只需要用户资料、使用记录、评价反馈和 inbox 汇总时，从本文件导入即可。
本文件不接入试用过期关闭和版本更新提醒。
"""

from __future__ import annotations

from typing import Any

from .feedback_manager import append_feedback, show_feedback_dialog
from .usage_tracker import UsageTracker, get_usage_profile


def aggregate_feedback_records(
    target: str = "all",
    printer: Any = print,
) -> dict[str, int]:
    """汇总信息收集 inbox。target: all/local/developer。"""

    from .data_feedback_aggregator import aggregate_records

    return aggregate_records(target=target, printer=printer)


__all__ = [
    "UsageTracker",
    "append_feedback",
    "aggregate_feedback_records",
    "get_usage_profile",
    "show_feedback_dialog",
]
