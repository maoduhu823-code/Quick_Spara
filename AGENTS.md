# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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

### File Structure

```
Quick_Sparam/
├── Quick_Sparam_B.py      # 生产入口
├── QSB_test.py            # 本地调试入口（不打包）
├── main_window.py         # 主窗口 SParameterViewer_MainWin(QWidget)
├── sparam_core.py         # 纯逻辑层（无UI依赖）
├── app_utils.py           # Qt工具层
├── Frequency_Analysis2.py # 死代码，暂留，不导入
└── dialogs/
    ├── __init__.py
    ├── freq_analysis.py   # frequencyAnalysisDialog — 频域批量分析+Excel导出
    ├── cascade.py         # CascadeDialog — S参数级联配置
    ├── port_reduction.py  # PortReductionDialog — 端口阻抗端接/降阶
    ├── port_reorder.py    # PortOrderEditor — 端口拖拽重排序
    ├── se2diff.py         # DiffConversionDialog — 单端→差分转换
    ├── port_selector.py   # PortSelector — 端口多选选择器
    ├── port_name.py       # PortNameDialog — 端口命名（缺失时处理）
    └── loading.py         # LoadingDialog — 长耗时进度对话框
```

### Dependency Direction

```
main_window  →  sparam_core
main_window  →  app_utils
main_window  →  dialogs/*
dialogs/*    →  sparam_core
dialogs/*    →  app_utils
app_utils    ──(懒加载)──→  dialogs/port_selector, port_name
```

`app_utils.check_and_set_port_names` 用函数体内懒导入 dialogs，避免循环依赖。

### Entry Points
- `Quick_Sparam_B.py` — 生产入口：配置 matplotlib 中文字体，创建 `QApplication`，实例化主窗口，调用 `check_beta_period()` 后进入事件循环。
- `QSB_test.py` — 本地调试入口，启动后自动执行加载文件等操作，不随 PyInstaller 打包。

### Main Window (`main_window.py`)
`SParameterViewer_MainWin(QWidget)` 拥有：
- `self.s_data`: `{filename → skrf.Network}` 的全局数据字典
- `self.s_param / y_param / z_param`: 计算后的参数矩阵字典
- `get_network(file_name)` / `get_s/y/z()` — 数据访问方法（懒加载+缓存）
- 左栏：文件操作、端口操作（降阶/重排/级联）、差分转换、频域分析
- 右栏：绘图控制（端口对输入、数据模式、纹波拟合）
- 内嵌 `QTextEdit` 控制台（重定向 stdout）

### Logic Layer (`sparam_core.py`)
- **网络变换**：`enforce_nonzero_impedance`, `enforce_nonzero_z0`, `SE2diff`, `SE2dq_dqs`, `SE2diff_port`
- **纹波分析**：`ripple_calc`, `ripple_calc1`, `_ieee_8023_fit`（多项式/IEEE 802.3-2022/Savitzky-Golay）
- **端口解析**：`parse_port_input`, `parse_port_input1`（支持 `"1 2 3"` / `"1:5"` / `"1:2:5"` 格式）
- 注意：`enforce_nonzero_impedance` 内部含一个 QDialog，是该层唯一的UI依赖

### Qt Utility Layer (`app_utils.py`)
- `show_error` — 统一错误弹窗
- `resource_path` — PyInstaller 冻结环境下的资源路径解析
- `freq_band_data_extract` — 频段标注绘图辅助
- `plot_main_curves` / `plot_residuals` — 通用绘图函数
- `check_and_set_port_names` — 端口名UI流程（懒导入 dialogs）

### matplotlib Backend
不要在模块级调用 `matplotlib.use()`。环境同时安装了 PyQt5 和 PyQt6，`Qt5Agg` 后端与 PyQt6 不兼容，会导致频域分析对话框闪退。让 matplotlib 自动检测后端（`QtAgg` → Qt6Agg）。

### Chinese Locale
所有UI字符串和注释均为简体中文。字体设置（Windows: `SimHei`，Linux: `WenQuanYi Zen Hei`）在 `Quick_Sparam_B.py` 全局配置，同时设置 `axes.unicode_minus = False` 避免负号渲染问题。
