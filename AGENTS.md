# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.
See also: `CLAUDE.md` (Claude Code guidance, kept in sync).

## Project Overview

Quick_Sparam is a PyQt6-based desktop GUI application for viewing and analyzing RF S-parameter files (Touchstone `.snp` format). Developed by 封装SIPI开发部.

## Running the Application

```bash
python Quick_Sparam_B.py
```

## Architecture (current state after refactor Phase 1–3)

```
Quick_Sparam/
├── Quick_Sparam_B.py           # Production entry
├── QSB_test.py                 # Local debug entry (not packaged)
├── main_window.py              # Main window (~1 390 lines, under active slimming)
├── sparam_core.py              # Backward-compat re-export shim
├── app_utils.py                # Qt utility layer (error dialogs, port name UI, plotting helpers)
│
├── QS_domain/                  # Domain layer — pure Python, no Qt/network
│   ├── algorithms/             # ripple.py, se2diff.py, time_domain.py, impedance.py, port_merge.py
│   ├── display_config.py       # Unified FACET_OPTIONS + DEFAULT_SCALES (single source of truth)
│   ├── enums.py                # ParamType, DisplayMode, FitMethod
│   └── port_parser.py          # parse_port_input (merged, single implementation)
│
├── QS_services/                # Application layer — no Qt
│   ├── network_service.py      # NetworkService + NetworkLoadError
│   └── plotting_service.py     # Data transformation (compute_param_data)
│
├── QS_infra/                   # Infrastructure layer
│   ├── cache.py                # NetworkCache (fingerprint-based)
│   └── resource_path.py        # PyInstaller path resolver
│
├── QS_dialogs/                 # UI dialogs (Qt)
│   ├── cascade.py, se2diff.py, port_reduction.py, port_reorder.py
│   ├── port_merge.py, port_management.py, port_selector.py, port_name.py
│   ├── ripple.py               # Accepts network_service injection (decoupled from parent)
│   ├── freq_analysis.py        # Heavy dialog (~1 800 lines)
│   ├── time_domain.py
│   └── loading.py
│
├── QS_runtime_services/        # License, usage tracking, feedback (do not modify)
│
├── samples/                    # Sample .snp files used by tests and docs
├── tests/                      # pytest suite (75 tests)
│   ├── domain/, infra/, services/, compat/
└── dev_scripts/                # Standalone validation/smoke scripts (not pytest)
```

## Key Rules

- **No PyQt6 in QS_domain/ or QS_services/** — violations are caught by the test suite
- **sparam_core.py** is a shim; all logic lives in QS_domain/
- Never call `matplotlib.use()` at module level — Qt5Agg + PyQt6 conflict
- All UI strings are Simplified Chinese
- Run `python -m pytest tests/ -q` before committing
