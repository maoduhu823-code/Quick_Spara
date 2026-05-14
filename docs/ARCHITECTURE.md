# ARCHITECTURE — 分层结构与模块职责

> Tier 1 文档：按需加载。先读 `AGENT_GUIDE.md` §四 的任务路由表，再决定要读本文哪一节。
> 行数与签名以代码为准；本文档落后于代码时**以代码为准**，并顺手更新本文。

---

## 一、模块树（截至本文档最近一次刷新）

```
Quick_Sparam/
├── Quick_Sparam_B.py            (26)    生产入口：QApplication + 试用校验 + 启动后续
├── QSB_test.py                  (31)    本地调试入口，不进 PyInstaller
├── Quick_Sparam_install.py      (31)    安装脚本
├── main_window.py             (1216)    SParameterViewer_MainWin（仍在瘦身）
├── app_utils.py                (131)    Qt 工具层（错误弹窗、字体、绘图辅助）
├── sparam_core.py               (45)    向后兼容 shim — 只做 re-export
│
├── QS_domain/                            领域层（纯 Python，禁止 PyQt6）
│   ├── enums.py                 (28)    ParamType / DisplayMode / FitMethod
│   ├── display_config.py        (19)    FACET_OPTIONS + DEFAULT_SCALES（单一事实源）
│   ├── port_parser.py           (60)    parse_port_input（纯算法）
│   └── algorithms/
│       ├── impedance.py         (40)    端口阻抗检查与修正
│       ├── ripple.py           (107)    纹波拟合（多项式 / IEEE 802.3-2022 / Savitzky-Golay）
│       ├── se2diff.py          (175)    单端→差分/混合模式转换（3 个公共函数）
│       ├── time_domain.py      (165)    时域变换（TDR / step / impulse / pulse）
│       └── port_merge.py        (46)    端口并联合并
│
├── QS_services/                          应用服务层（禁止 PyQt6）
│   ├── network_service.py       (73)    NetworkService + NetworkLoadError
│   └── plotting_service.py      (55)    compute_param_data / get_axis_labels / get_default_scales
│
├── QS_infra/                             基础设施层
│   ├── cache.py                 (95)    NetworkCache（基于 mtime+size 指纹）
│   └── resource_path.py         (10)    PyInstaller 路径解析
│
├── QS_dialogs/                           UI 对话框（Qt）
│   ├── freq_analysis.py       (1606)    重型：频域批量分析 + Excel 导出
│   ├── time_domain.py          (429)    时域分析对话框
│   ├── cascade.py              (253)    S 参数级联
│   ├── port_reduction.py       (233)    端口阻抗端接/降阶
│   ├── se2diff.py              (193)    单端→差分对话框
│   ├── ripple.py               (176)    纹波分析（接受 network_service 注入）
│   ├── port_merge.py           (151)    端口合并
│   ├── port_management.py      (120)    端口管理总入口
│   ├── port_name.py             (73)    端口命名补全
│   ├── port_selector.py         (56)    端口多选选择器
│   ├── port_reorder.py          (51)    拖拽重排序
│   └── loading.py               (40)    长耗时进度框
│
├── QS_runtime_services/                  独立子系统（许可/版本/反馈，不要改动）
│   ├── trial_manager.py        (384)    试用期校验
│   ├── version_manager.py      (301)    版本检查与异步更新
│   ├── usage_tracker.py        (400)    使用统计
│   ├── feedback_manager.py     (291)    用户反馈
│   ├── data_feedback_aggregator.py (529)
│   └── ...
│
├── samples/                              .snp 样本（s2p/s4p）
├── tests/                                pytest 套件
│   ├── domain/  test_port_parser.py · test_ripple.py
│   ├── services/ test_network_service.py · test_plotting_service.py
│   ├── infra/   test_cache.py
│   └── compat/  test_sparam_core.py（保护向后兼容入口）
├── dev_scripts/                          非 pytest 冒烟脚本
└── docs/                                 文档（含本文件、archive/）
```

## 二、各层职责与边界

### §QS_domain — 领域层
- **职责**：所有纯算法实现。复数矩阵运算、拟合、字符串解析、时域 FFT。
- **依赖**：仅 numpy / scipy / scikit-rf。**不能** import PyQt、matplotlib、`QS_services` 或 `QS_dialogs`。
- **错误处理**：抛 `ValueError` / `RuntimeError`，由上层翻译为 UI 提示。
- **特例**：`enforce_nonzero_z0` 在 `impedance.py` 不弹窗——只读取文件首行 `#` 后的参考阻抗自动修正。需要弹窗询问的旧路径已迁到调用方。

### §QS_services — 应用服务层
- **职责**：协调 domain 算法与 infra 缓存，提供给 UI 调用的稳定接口。
- **依赖**：numpy / scikit-rf / `QS_domain` / `QS_infra`。**不能** import PyQt6。
- **当前两个服务**：
  - `NetworkService` — 文件加载、缓存协调、S/Y/Z 矩阵懒计算；UI 通过 `parent.get_network()` 委托到此对象。
  - 绘图数据变换函数（不是类）：`compute_param_data` 把复数切片转换成可绘的实数 + 轴标签。

### §QS_infra — 基础设施层
- **职责**：与外部世界对接的最薄层。当前两件事：
  - `NetworkCache` — 基于 mtime+size 指纹的 Network/参数矩阵缓存；磁盘文件变化自动失效，内存生成的 Network 注册时 `fingerprint=None`。
  - `resource_path` — PyInstaller 冻结环境下的资源解析（依赖 `sys._MEIPASS`）。

### §QS_dialogs — UI 对话框
- **职责**：所有 QDialog 子类。直接持有 matplotlib `Figure` 嵌入对话框，禁止依赖主窗口字段；需要数据时通过构造参数注入（参考 `ripple.py` 接受 `network_service`）。
- **风险点**：`freq_analysis.py` 已到 1606 行，是下一阶段需要拆分的重型对话框，但目前不要顺手拆。

### §main_window
- **职责**：组合根。持有 `NetworkService` 实例，向对话框暴露 `get_network / register_network / invalidate_file_cache / clear_all_cache`（这些方法在 main_window 上是 NetworkService 的薄包装）。
- **当前体量**：1216 行，目标 < 600。剥离对象：matplotlib 状态、文件列表 widget 操作、绘图分发。
- **入口**：详见 `INTERFACES.md` §main_window（仅列对话框可调用的公共方法）。

### §app_utils
- **角色**：Qt 工具，不属于分层架构，但允许被 main_window / QS_dialogs 调用。
- **关键函数**：`show_error`、`configure_matplotlib`、`plot_main_curves`、`plot_residuals`、`freq_band_data_extract`、`check_and_set_port_names`。
- **懒导入**：`check_and_set_port_names` 函数体内才 `from QS_dialogs.port_selector import ...`，避免循环依赖。

### §sparam_core（兼容 shim）
- 只 re-export `QS_domain.*` 中的实现；唯一带额外逻辑的是 `parse_port_input`（把 `ValueError` 翻译成 `QMessageBox`）。
- **新代码请直接 import `QS_domain` 子模块**；shim 仅保护既有调用方。
- `tests/compat/test_sparam_core.py` 防止 shim 入口被误删。

## 三、关键非显式约定

- **`debug` 开关**：`NetworkService.debug` setter 直接代理到 `NetworkCache.debug`，控制缓存日志。
- **参数类型字符串**：`'S参数' / 'Y参数' / 'Z参数' / '时域'` 是跨层流通的事实标签，`QS_domain/enums.py` 的 `ParamType` 是其规范定义；改名要同步 `display_config.FACET_OPTIONS` 的 key。
- **端口编号**：domain 层接口统一 1-based（如 `ripple_calc(network, p1, p2, ...)`，`merge_ports_multi` 内部 0-based）；UI 层与 domain 接口对齐使用 1-based。
- **网络名约定**：算法产生新 Network 时按 `<原name>_<操作>_<参数>.s<N>p` 命名，便于文件列表展示与后续保存。
