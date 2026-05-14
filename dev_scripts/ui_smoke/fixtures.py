from __future__ import annotations

from pathlib import Path

import skrf as rf
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView

from .harness import SmokeContext


PREFERRED_FILES = [
    "diff_line.s4p",
    "connector_model.s4p",
    "StackupDemo1_test_renorm_R.s2p",
    "Via_L14.s4p",
]


def resolve_input_dir(repo_root: Path, user_input_dir: str | None) -> Path:
    if user_input_dir:
        return Path(user_input_dir).expanduser().resolve()
    input_dir = repo_root / "input"
    if input_dir.exists():
        return input_dir
    return repo_root / "samples"


def discover_sample_files(ctx: SmokeContext) -> list[Path]:
    input_dir = resolve_input_dir(ctx.repo_root, ctx.args.input_dir)
    files: list[Path] = []
    for name in PREFERRED_FILES:
        candidate = input_dir / name
        if candidate.exists():
            files.append(candidate)
    for candidate in sorted(input_dir.glob("*.s*p")) + sorted(input_dir.glob("*.S*P")):
        if candidate not in files:
            files.append(candidate)
    limit = max(1, ctx.args.limit_samples)
    ctx.sample_files = files[:limit]
    if not ctx.sample_files:
        raise FileNotFoundError(f"No Touchstone files found in {input_dir}")
    return ctx.sample_files


def ensure_viewer(ctx: SmokeContext):
    if ctx.viewer is not None:
        if ctx.viewer.file_list.count() == 0:
            load_files_into_viewer(ctx, ctx.viewer)
        else:
            select_files(ctx.viewer, range(min(2, ctx.viewer.file_list.count())))
        return ctx.viewer

    from app_utils import configure_matplotlib
    from main_window import SParameterViewer_MainWin

    configure_matplotlib()
    viewer = SParameterViewer_MainWin(enable_time_domain=True)
    ctx.viewer = viewer
    ctx.show_widget(viewer, 1500, 760)
    ctx.install_port_selection_patch()
    load_files_into_viewer(ctx, viewer)
    return viewer


def load_files_into_viewer(ctx: SmokeContext, viewer) -> None:
    if not ctx.sample_files:
        discover_sample_files(ctx)
    existing = set(viewer.get_all_file_keys())
    for file_path in ctx.sample_files:
        key = str(file_path)
        if key not in existing:
            viewer.add_file_list_item(key)
        network = viewer.get_network(key)
        ensure_port_names(network)
    viewer.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    select_files(viewer, range(min(2, viewer.file_list.count())))


def ensure_port_names(network: rf.Network) -> None:
    if not network.port_names:
        network.port_names = [f"Port{i + 1}" for i in range(network.nports)]


def select_files(viewer, rows) -> None:
    viewer.file_list.clearSelection()
    for row in rows:
        item = viewer.file_list.item(row)
        if item is not None:
            item.setSelected(True)
            viewer.file_list.setCurrentItem(item)


def first_file(viewer) -> str:
    if viewer.file_list.count() == 0:
        raise RuntimeError("No files loaded in viewer")
    return viewer.get_file_key_from_item(viewer.file_list.item(0))


def first_network(viewer) -> rf.Network:
    return viewer.get_network(first_file(viewer))


def selected_file_keys(viewer) -> list[str]:
    files = viewer.get_selected_file_keys()
    if files:
        return files
    select_files(viewer, [0])
    return viewer.get_selected_file_keys()
