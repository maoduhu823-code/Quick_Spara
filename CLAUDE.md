# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quick_Sparam is a PyQt6-based desktop GUI application for viewing and analyzing RF S-parameter files (Touchstone `.snp` format). It is developed by the 封装SIPI开发部 (Package SIPI Development Dept). The application is distributed as a standalone `.exe` via PyInstaller.

## Running the Application

```bash
python Quick_Sparam_B.py
```

## Building the Executable

The project uses PyInstaller (via `auto-py-to-exe`) to produce a standalone `.exe`:

```bash
auto-py-to-exe
# or directly:
pyinstaller Quick_Sparam_B.py
```

## Installing Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies: `PyQt6`, `scikit-rf` (`skrf`), `numpy`, `scipy`, `matplotlib`, `pandas`, `openpyxl`.

## Architecture

### Entry Point
`Quick_Sparam_B.py` — sets matplotlib font/backend globals for Windows/Linux, creates the `QApplication`, instantiates `SParameterViewer_MainWin`, and calls `check_beta_period()` before entering the event loop.

### Main Window
`Quick_Sparam_mainUI.py` — defines `SParameterViewer_MainWin(QWidget)`, the entire application window. It owns:
- `self.s_data`: dict mapping filename → `skrf.Network` objects
- `self.s_param / y_param / z_param`: dicts of computed parameter matrices
- Left panel: file operations (open/save/delete), port operations (reduction, reorder, cascade), diff conversion, frequency analysis
- Right panel: plot controls (port pair inputs, data mode combo, ripple fitting)
- An embedded `QTextEdit` output console (redirected stdout via `write()`)

### Core Functions (`Basic_function_module.py`)
Standalone functions used by all UI modules:
- `get_network / get_s / get_y / get_z` — load Touchstone files via `skrf.Network`
- `enforce_nonzero_impedance / enforce_nonzero_z0` — fix zero-valued port impedances (common in some EDA exports)
- `SE2diff / SE2dq_dqs / SE2diff_port` — single-ended to differential/mixed-mode conversion
- `ripple_calc / ripple_calc1` — S-parameter ripple analysis with polynomial, IEEE 802.3-2022, or Savitzky-Golay smoothing fits
- `parse_port_input / parse_port_input1` — parse port range strings like `"1 2 3"` or `"1:5"` or `"1:2:5"`
- `freq_band_data_extract` — extract and annotate frequency-band data on plots
- `resource_path` — resolves asset paths for both dev and PyInstaller frozen environments

### Dialog Modules
- `UI2_Port_reduction.py` — `PortReductionDialog`: UI for port impedance termination/reduction, produces a reduced `skrf.Network`
- `UI2_Cascade.py` — `SParamCascadeDialog`: S-parameter cascading configuration dialog; receives a list of selected S-parameter files and returns `cascade_configs`
- `UI2_PortOrderEditor.py` — `PortOrderEditor`: drag-and-drop port reordering dialog
- `UI2_SE2Diff.py` — `DiffConversionDialog`: single-ended to differential conversion settings (noted in source as UI debug incomplete / port naming bug)
- `UI2_Frequency_Analysis.py` — `frequencyAnalysisDialog`: batch S-parameter frequency-domain analysis with Excel export; takes `(S_data, parent)`; **this is the version imported by the main window**
- `Frequency_Analysis2.py` — newer version of the same dialog, takes `(S_data, s_params_files, parent)`; not currently imported by any module, kept for future migration
- `Longtime_block_hint.py` — `LoadingDialog`: indeterminate progress dialog for long-running operations; designed for use with a `QThread` worker; exposes `cancelled` flag and `set_message()` for live updates
- `portname_setting.py` — `PortNameDialog`: handles missing port names in Touchstone files; offers manual edit (opens notepad/gvim), auto-generate (`Port1…PortN`), or cancel
- `UI2_PortSelection.py` — `PortSelector`: multi-select port picker dialog; returns 1-based selected indices via `get_selected_indices()`; also exposes `PortSelector.select_ports(port_names, parent)` static helper

### Notes on Duplicate Files
`Frequency_Analysis2.py` and `UI2_Frequency_Analysis.py` define the same class name (`frequencyAnalysisDialog`). The main window imports from `UI2_Frequency_Analysis.py` (old version, `(S_data, parent)`). `Frequency_Analysis2.py` is a newer unconnected version.

### matplotlib Backend
Both `Frequency_Analysis2.py` and `UI2_Frequency_Analysis.py` call `matplotlib.use('Qt5Agg')` at module level. The environment has both PyQt5 and PyQt6 installed; the runtime Qt backend must stay consistent with whichever Qt binding is active. This call must appear before any `plt` imports take effect.

### Chinese Locale
All UI strings and comments are in Simplified Chinese. Font settings (`SimHei` on Windows, `WenQuanYi Zen Hei` on Linux) are applied globally in `Quick_Sparam_B.py` and locally in some dialogs to support Chinese labels and avoid minus-sign rendering issues (`axes.unicode_minus = False`).
