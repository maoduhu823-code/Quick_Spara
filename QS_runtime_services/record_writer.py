"""
后台记录投递工具。

软件运行时不再直接写共享 Excel，而是把每次提交写成独立 JSON 小文件：
data_feedback/inbox/usage_用户名_时间戳_记录ID.json

后续由 data_feedback_aggregator.py 定时汇总到 summary Excel，并在汇总成功后删除
这些独立小文件。这样多人同时提交时只会创建不同文件，避免共享 Excel 文件锁。
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from threading import Thread
from typing import Any
import uuid

try:
    from .notice_manager import ACCESS_UNAVAILABLE_MESSAGE, print_access_unavailable_once
except ImportError:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from QS_runtime_services.notice_manager import (
        ACCESS_UNAVAILABLE_MESSAGE,
        print_access_unavailable_once,
    )

PATH_WRITE_TIMEOUT_SECONDS = 10
RECORD_SCHEMA_VERSION = 1


def submit_record_async(
    record_name: str,
    sheet_name: str,
    headers: list[str],
    row: list[Any],
    local_inbox_dirs: list[Path],
    developer_inbox_dirs: list[Path],
) -> None:
    """后台投递一条记录 JSON 到本地 inbox 和开发者 inbox。"""
    worker = Thread(
        target=_submit_record_worker,
        args=(
            record_name,
            sheet_name,
            headers,
            row,
            local_inbox_dirs,
            developer_inbox_dirs,
        ),
        daemon=True,
        name=f"{record_name}_record_writer",
    )
    worker.start()


def configured_paths(mapping: dict[str, Any], app_base_dir: Path) -> list[Path]:
    configured = _platform_value(mapping)
    if configured is None:
        return []
    if isinstance(configured, (str, os.PathLike)):
        configured = [configured]

    paths: list[Path] = []
    for raw_path in configured:
        path = Path(os.path.expandvars(os.path.expanduser(str(raw_path))))
        if not path.is_absolute():
            path = app_base_dir / path
        paths.append(path)
    return paths


def _submit_record_worker(
    record_name: str,
    sheet_name: str,
    headers: list[str],
    row: list[Any],
    local_inbox_dirs: list[Path],
    developer_inbox_dirs: list[Path],
) -> None:
    payload = _build_payload(record_name, sheet_name, headers, row)
    prefix = _record_prefix(sheet_name)

    local_written_dir = None
    if local_inbox_dirs:
        local_written_dir = _write_first_available_inbox(
            record_name, "本地", payload, _unique_paths(local_inbox_dirs), prefix
        )
    if developer_inbox_dirs:
        developer_candidates = _unique_paths(developer_inbox_dirs, skip={local_written_dir})
        if developer_candidates:
            _write_first_available_inbox(
                record_name, "开发者", payload, developer_candidates, prefix
            )
    if not local_inbox_dirs and not developer_inbox_dirs:
        print_access_unavailable_once()


def _build_payload(
    record_name: str, sheet_name: str, headers: list[str], row: list[Any]
) -> dict[str, Any]:
    record = {
        str(header): row[index] if index < len(row) else ""
        for index, header in enumerate(headers)
    }
    record_type = _record_prefix(sheet_name)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "record_id": _make_record_id(record_type, record),
        "record_type": record_type,
        "record_name": record_name,
        "sheet_name": sheet_name,
        "record": record,
        "created_at": _now_text(),
    }


def _make_record_id(record_type: str, record: dict[str, Any]) -> str:
    if record_type != "user_data":
        return uuid.uuid4().hex

    normalized = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    host_name = _safe_filename_part(str(record.get("主机名", ""))) or "unknown"
    return f"user_data_{host_name}_{digest}"


def _write_first_available_inbox(
    record_name: str,
    target_name: str,
    payload: dict[str, Any],
    inbox_dirs: list[Path],
    prefix: str,
) -> Path | None:
    if not inbox_dirs:
        print_access_unavailable_once()
        return None

    for inbox_dir in inbox_dirs:
        ok, _error = _write_payload_with_timeout(inbox_dir, payload, prefix)
        if ok:
            return inbox_dir

    print_access_unavailable_once()
    return None


def _write_payload_with_timeout(
    inbox_dir: Path, payload: dict[str, Any], prefix: str
) -> tuple[bool, str]:
    result: dict[str, Any] = {}

    def write_once() -> None:
        try:
            _write_payload_file(inbox_dir, payload, prefix)
            result["ok"] = True
        except Exception as exc:
            result["error"] = str(exc)

    worker = Thread(target=write_once, daemon=True, name=f"inbox_writer_{inbox_dir.name}")
    worker.start()
    worker.join(PATH_WRITE_TIMEOUT_SECONDS)
    if worker.is_alive():
        return False, f"超过 {PATH_WRITE_TIMEOUT_SECONDS}s 未响应"
    if result.get("ok"):
        return True, ""
    return False, result.get("error", "未知写入错误")


def _write_payload_file(inbox_dir: Path, payload: dict[str, Any], prefix: str) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)

    filename = _record_filename(prefix, payload)
    final_path = inbox_dir / filename
    temp_path = inbox_dir / f".{filename}.{uuid.uuid4().hex}.tmp"
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    temp_path.replace(final_path)
    return final_path


def _record_filename(prefix: str, payload: dict[str, Any]) -> str:
    record = payload.get("record", {})
    user = str(record.get("用户姓名") or record.get("主机名") or "unknown")
    user = _safe_filename_part(user)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    record_id = str(payload.get("record_id", uuid.uuid4().hex))[:12]
    return f"{prefix}_{user}_{timestamp}_{record_id}.json"


def _record_prefix(sheet_name: str) -> str:
    if sheet_name == "用户信息":
        return "user_data"
    if sheet_name == "评价反馈":
        return "feedback"
    return "usage"


def _safe_filename_part(value: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value.strip(), flags=re.UNICODE)
    return text.strip("._") or "unknown"


def _unique_paths(paths: list[Path], skip: set[Path | None] | None = None) -> list[Path]:
    skip_keys = {_path_key(path) for path in (skip or set()) if path is not None}
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = _path_key(path)
        if key in skip_keys or key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path))


def _platform_value(mapping: dict[str, Any]) -> Any:
    if sys.platform in mapping:
        return mapping[sys.platform]
    if sys.platform.startswith("linux") and "linux" in mapping:
        return mapping["linux"]
    return mapping.get("default")


def _now_text() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


# 兼容旧调用名。当前语义已经从“直接追加 Excel”变为“投递 JSON 记录文件”。
append_excel_row_async = submit_record_async
