from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QDialog,
    QInputDialog,
    QMessageBox,
    QWidget,
)

from .report import SmokeReport, Timer


class SmokeContext:
    def __init__(self, args: Any, repo_root: Path) -> None:
        self.args = args
        self.repo_root = repo_root
        self.report = SmokeReport()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="quick_sparam_ui_smoke_"))
        self.sample_files: list[Path] = []
        self.viewer: QWidget | None = None
        self.app = QApplication.instance() or QApplication(sys.argv[:1])
        self._patches: list[tuple[Any, str, Any]] = []
        self._old_excepthook: Callable[..., Any] | None = None
        self._current_module = "harness"
        self._current_case = "startup"
        self._step_failed = False

    def __enter__(self) -> "SmokeContext":
        self.install_patches()
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        self.close_mpl_figures()
        self.restore_patches()

    def patch_attr(self, obj: Any, attr: str, value: Any) -> None:
        old = getattr(obj, attr)
        self._patches.append((obj, attr, old))
        setattr(obj, attr, value)

    def install_patches(self) -> None:
        self._old_excepthook = sys.excepthook

        def excepthook(exc_type, exc_value, exc_tb):
            detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            self._step_failed = True
            self.report.fail(self._current_module, self._current_case,
                             f"uncaught Qt exception: {detail}")

        sys.excepthook = excepthook

        def message(kind: str, status: str = "WARN"):
            def _impl(parent, title, text, *args, **kwargs):
                if status == "FAIL":
                    self._step_failed = True
                    self.report.fail(self._current_module, f"{kind}: {title}", str(text))
                elif status == "PASS":
                    self.report.ok(self._current_module, f"{kind}: {title}", str(text))
                else:
                    self.report.warn(self._current_module, f"{kind}: {title}", str(text))
                return QMessageBox.StandardButton.Ok
            return staticmethod(_impl)

        self.patch_attr(QMessageBox, "warning", message("message warning"))
        self.patch_attr(QMessageBox, "information",
                        message("message information", status="PASS"))
        self.patch_attr(QMessageBox, "critical",
                        message("message critical", status="FAIL"))

        def question(parent, title, text, *args, **kwargs):
            self.report.warn(self._current_module, f"message question: {title}", str(text))
            return QMessageBox.StandardButton.Yes

        self.patch_attr(QMessageBox, "question", staticmethod(question))

        def get_open_file_names(parent=None, caption="", directory="", filter=""):
            return ([str(p) for p in self.sample_files], "S 参数文件 (*.s*p *.S*P)")

        def get_save_file_name(parent=None, caption="", directory="", filter=""):
            suffix = ".xlsx" if "Excel" in filter or "xlsx" in filter else ".txt"
            return (str(self.temp_dir / f"smoke_output{suffix}"), filter)

        def get_existing_directory(parent=None, caption="", directory="", options=None):
            return str(self.temp_dir)

        self.patch_attr(QFileDialog, "getOpenFileNames", staticmethod(get_open_file_names))
        self.patch_attr(QFileDialog, "getSaveFileName", staticmethod(get_save_file_name))
        self.patch_attr(QFileDialog, "getExistingDirectory", staticmethod(get_existing_directory))
        self.patch_attr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("1~5", True)))
        self.patch_attr(QInputDialog, "getDouble", staticmethod(lambda *a, **k: (50.0, True)))

        class DummyProcess:
            pid = 0

            def poll(self):
                return 0

        def fake_popen(*args, **kwargs):
            self.report.ok(self._current_module, "external process suppressed",
                           "subprocess.Popen was replaced during smoke run")
            return DummyProcess()

        self.patch_attr(subprocess, "Popen", fake_popen)

        try:
            import matplotlib.pyplot as plt

            old_show = plt.show

            def non_blocking_show(*args, **kwargs):
                kwargs.setdefault("block", False)
                return old_show(*args, **kwargs)

            self.patch_attr(plt, "show", non_blocking_show)
        except Exception:
            pass

    def restore_patches(self) -> None:
        for obj, attr, old in reversed(self._patches):
            setattr(obj, attr, old)
        self._patches.clear()
        if self._old_excepthook is not None:
            sys.excepthook = self._old_excepthook

    def install_port_selection_patch(self) -> None:
        def fake_check_and_set_port_names(parent, file_list, network_service=None):
            return [1, 2]

        module_names = [
            "app_utils",
            "main_window",
            "QS_dialogs.port_merge",
            "QS_dialogs.port_reduction",
            "QS_dialogs.time_domain",
        ]
        for module_name in module_names:
            module = sys.modules.get(module_name)
            if module and hasattr(module, "check_and_set_port_names"):
                self.patch_attr(module, "check_and_set_port_names",
                                fake_check_and_set_port_names)

        try:
            from QS_dialogs.port_selector import PortSelector

            self.patch_attr(
                PortSelector,
                "select_ports",
                staticmethod(lambda port_names, parent=None:
                             (QDialog.DialogCode.Accepted, [1, 2])),
            )
        except Exception:
            pass

        try:
            import main_window

            self.patch_attr(main_window, "show_feedback_dialog",
                            lambda parent=None: None)
        except Exception:
            pass

    def process_events(self, ms: int | None = None) -> None:
        delay = self.args.pause_ms if ms is None else ms
        end = time.perf_counter() + max(0, delay) / 1000
        while time.perf_counter() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.app.processEvents()

    def step(self, module: str, case: str, func: Callable[[], Any]) -> Any:
        self._current_module = module
        self._current_case = case
        self._step_failed = False
        with Timer() as timer:
            try:
                result = func()
                self.process_events()
                self.close_message_boxes()
                if not self._step_failed:
                    self.report.ok(module, case, elapsed_ms=timer.elapsed_ms)
                return result
            except Exception:
                self._step_failed = True
                self.report.fail(module, case, traceback.format_exc(),
                                 elapsed_ms=timer.elapsed_ms)
                return None

    def show_widget(self, widget: QWidget, width: int | None = None,
                    height: int | None = None) -> None:
        if width and height:
            widget.resize(width, height)
        widget.show()
        widget.raise_()
        widget.activateWindow()
        self.process_events()

    def close_widget(self, widget: QWidget | None) -> None:
        if widget is not None:
            try:
                widget.close()
                self.process_events(20)
            except RuntimeError as exc:
                if "has been deleted" not in str(exc):
                    raise

    def close_message_boxes(self) -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMessageBox):
                widget.done(0)

    def close_mpl_figures(self) -> None:
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except Exception:
            pass

    def keep_open_if_requested(self) -> None:
        if self.args.keep_open_ms > 0:
            self.process_events(self.args.keep_open_ms)


def configure_environment() -> None:
    os.environ.setdefault("SKRF_PLOT_ENV", "none")
