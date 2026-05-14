from __future__ import annotations

from dataclasses import dataclass
import sys
from time import perf_counter


@dataclass
class SmokeResult:
    module: str
    case: str
    status: str
    detail: str = ""
    elapsed_ms: float = 0.0


class SmokeReport:
    def __init__(self) -> None:
        self.results: list[SmokeResult] = []

    def add(self, module: str, case: str, status: str,
            detail: str = "", elapsed_ms: float = 0.0) -> None:
        self.results.append(SmokeResult(module, case, status, detail, elapsed_ms))

    def ok(self, module: str, case: str,
           detail: str = "", elapsed_ms: float = 0.0) -> None:
        self.add(module, case, "PASS", detail, elapsed_ms)

    def warn(self, module: str, case: str,
             detail: str = "", elapsed_ms: float = 0.0) -> None:
        self.add(module, case, "WARN", detail, elapsed_ms)

    def fail(self, module: str, case: str,
             detail: str = "", elapsed_ms: float = 0.0) -> None:
        self.add(module, case, "FAIL", detail, elapsed_ms)

    @property
    def fail_count(self) -> int:
        return sum(1 for item in self.results if item.status == "FAIL")

    @property
    def warn_count(self) -> int:
        return sum(1 for item in self.results if item.status == "WARN")

    @property
    def pass_count(self) -> int:
        return sum(1 for item in self.results if item.status == "PASS")

    def print_summary(self) -> None:
        out = sys.__stderr__ or sys.__stdout__ or sys.stdout
        def emit(text: str) -> None:
            encoding = getattr(out, "encoding", None) or "utf-8"
            safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
            print(safe, file=out)

        emit("\n=== Quick_Sparam visible UI smoke summary ===")
        emit(f"PASS: {self.pass_count}  WARN: {self.warn_count}  FAIL: {self.fail_count}")
        for item in self.results:
            duration = f" ({item.elapsed_ms:.0f} ms)" if item.elapsed_ms else ""
            detail = f" - {item.detail}" if item.detail else ""
            emit(f"[{item.status}] {item.module} :: {item.case}{duration}{detail}")


class Timer:
    def __enter__(self) -> "Timer":
        self.started = perf_counter()
        self.elapsed_ms = 0.0
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed_ms = (perf_counter() - self.started) * 1000
