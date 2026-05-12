# Quick_Sparam 代码架构重组方案

> 版本：1.1 | 日期：2026-05-12 | 作者：架构审查 → Claude Code 持续推进

---

## 一、现状评估

### 1.1 模块规模速览

| 文件 | 行数 | 主要职责 |
|------|------|---------|
| `main_window.py` | 1 518 | 主窗口 — UI + 缓存 + 绘图 + 业务逻辑全混杂 |
| `dialogs/freq_analysis.py` | 1 854 | 频域分析对话框 — 本身已接近主窗口体量 |
| `sparam_core.py` | 765 | 算法核心 — 多领域混杂于一文件 |
| `runtime_services/trial_manager.py` | 480 | 许可/试用管理 |
| `runtime_services/usage_tracker.py` | 472 | 使用统计 |
| `dialogs/time_domain.py` | 496 | 时域分析 |
| `app_utils.py` | 155 | 杂项工具 |

项目总体规模约 **8 000 行有效代码**，功能完整，但结构债务已较明显。

### 1.2 主要结构问题

#### 问题 A — 巨型主窗口（God Object）

`SParameterViewer_MainWin` 同时承担：
- Qt 布局与事件响应
- 多文件缓存管理（S/Y/Z 参数字典 + 指纹映射）
- matplotlib 绘图状态（`self.fig`, `self.ax`, `self.plot_lines`）
- 业务逻辑调度（调用 13 个对话框）
- 控制台重定向

单一类 40+ 方法，严重违背单一职责原则（SRP）。

#### 问题 B — 算法模块边界模糊

`sparam_core.py` 混合了四个完全独立的领域：
- 阻抗约束（`enforce_nonzero_impedance`）
- 差分转换（`SE2diff`, `SE2dq_dqs`）
- 纹波分析（`ripple_calc`, `ripple_calc1`）
- 时域变换（`compute_time_domain`, `_td_*`）
- 端口字符串解析（`parse_port_input`）

任何领域扩展都需要读整个文件。

#### 问题 C — 双向耦合：主窗口 ↔ 对话框

对话框通过 `parent` 引用直接调用主窗口方法（`get_network()`, `register_network()`, `invalidate_file_cache()`），主窗口又直接 import 13 个对话框类。双向依赖使得任何一侧都无法独立测试。

#### 问题 D — 幻数字符串 / 魔法字典

参数类型（`'S参数'`, `'Y参数'`, `'Z参数'`, `'时域'`）和显示模式（`'幅度(dB)'` 等）以裸字符串传递，散落于 UI 事件、绘图逻辑和对话框之间。重命名或添加类型时需要全局搜索。

#### 问题 E — 重复代码

- `ripple_calc` / `ripple_calc1` — 两个几乎相同的函数，差异仅在绘图行为
- `parse_port_input` / `parse_port_input1` — 重复的端口字符串解析逻辑
- 多个对话框独立重复 matplotlib 字体配置代码

#### 问题 F — 测试盲区

所有业务逻辑都嵌在 Qt 组件内，脱离 `QApplication` 无法运行，导致自动化测试几乎不可行。

---

## 二、目标架构

采用**分层架构（Layered Architecture）**结合**依赖倒置（DIP）**，将代码按关注点分为四层：

```
┌─────────────────────────────────────────────────────┐
│              Presentation Layer（表现层）             │
│   ui/main_window.py  ·  dialogs/*.py                 │
│   只负责 Qt 布局、事件绑定、结果展示                   │
└────────────────────┬────────────────────────────────┘
                     │ 调用
┌────────────────────▼────────────────────────────────┐
│             Application Layer（应用层）               │
│   services/network_service.py                        │
│   services/plotting_service.py                       │
│   services/analysis_service.py                       │
│   协调用例执行，不含领域知识，不含 Qt 代码              │
└────────────────────┬────────────────────────────────┘
                     │ 调用
┌────────────────────▼────────────────────────────────┐
│              Domain Layer（领域层）                   │
│   domain/models.py          — 数据类/DTO              │
│   domain/algorithms/        — 纯算法，无 UI/网络依赖   │
│   domain/port_parser.py     — 端口字符串解析           │
└────────────────────┬────────────────────────────────┘
                     │ 调用
┌────────────────────▼────────────────────────────────┐
│           Infrastructure Layer（基础设施层）           │
│   infra/cache.py            — 网络对象缓存             │
│   infra/file_io.py          — SNP 文件读写             │
│   infra/resource_path.py    — PyInstaller 路径         │
│   runtime_services/         — 试用/更新/反馈（维持现状）│
└─────────────────────────────────────────────────────┘
```

### 2.1 实际文件结构（Phase 1-3 完成后）

> **命名说明**：所有新包使用 `QS_` 前缀作为项目命名空间，避免与标准库冲突。

```
Quick_Sparam/
├── Quick_Sparam_B.py           # 生产入口（维持现状）
├── QSB_test.py                 # 本地调试入口（不打包）
├── main_window.py              # 主窗口（~1 390 行，持续瘦身中）
├── sparam_core.py              # 向后兼容 re-export shim（过渡期保留）
├── app_utils.py                # Qt 工具层（过渡期保留）
│
├── QS_dialogs/                 # 表现层 — 对话框（Qt）
│   ├── ripple.py               # 已注入 network_service（解耦范例）
│   └── cascade.py, se2diff.py, port_reduction.py, ...
│
├── QS_services/                # 应用层（无 Qt）
│   ├── network_service.py      # NetworkService + NetworkLoadError
│   └── plotting_service.py     # 数据变换（compute_param_data）
│
├── QS_domain/                  # 领域层（纯 Python，无 Qt）
│   ├── display_config.py       # FACET_OPTIONS + DEFAULT_SCALES（单一来源）
│   ├── enums.py                # ParamType, DisplayMode, FitMethod
│   ├── port_parser.py          # parse_port_input（合并后单一实现）
│   └── algorithms/
│       ├── impedance.py        # has_zero_impedance / replace_zero_impedance（纯函数）
│       ├── se2diff.py          # SE2diff, SE2dq_dqs, SE2diff_port
│       ├── ripple.py           # ripple_calc（合并后）
│       ├── time_domain.py      # compute_time_domain 及辅助函数
│       └── port_merge.py       # merge_ports_multi
│
├── QS_infra/                   # 基础设施层
│   ├── cache.py                # NetworkCache（文件指纹）
│   └── resource_path.py        # PyInstaller 路径解析
│
├── QS_runtime_services/        # 运维服务（许可/统计/反馈，维持现状）
│
├── samples/                    # 示例 .snp 文件（供测试和文档使用）
├── tests/                      # pytest 测试套件
│   ├── domain/, infra/, services/, compat/
│   └── smoke/, scripts/        # 待补充
├── dev_scripts/                # 独立验证脚本（非 pytest）
└── docs/
    ├── architecture_refactor_plan.md
    └── architecture_refactor_acceptance.md
```

### 2.2 长期目标结构（Phase 4-6 完成后）

主窗口将继续拆分，最终目标 ≤ 600 行。`QS_dialogs/` 对话框不再通过 `self.parent()` 访问主窗口数据，改为注入服务或使用信号。

---

## 三、核心重构细节

### 3.1 拆解主窗口

当前 `main_window.py` 应拆分为三个关注点：

**`services/network_service.py`** — 管理 `skrf.Network` 对象集合

```python
class NetworkService:
    def __init__(self, cache: NetworkCache): ...
    def load_file(self, path: str) -> NetworkRecord: ...
    def get_network(self, name: str) -> skrf.Network: ...
    def register_network(self, name: str, ntwk: skrf.Network): ...
    def delete(self, name: str): ...
    def get_param_matrix(self, name: str, param: ParamType) -> np.ndarray: ...
    def invalidate(self, name: str): ...
```

**`services/plotting_service.py`** — 封装 matplotlib 状态

```python
class PlottingService:
    def __init__(self, canvas: FigureCanvas): ...
    def plot_curve(self, x, y, label, style): ...
    def clear(self): ...
    def set_axis_labels(self, xlabel, ylabel): ...
    def add_band_annotations(self, bands): ...
```

**`ui/main_window.py`** — 只负责布局和事件路由，注入 service

```python
class SParameterViewer_MainWin(QWidget):
    def __init__(self):
        self._net_svc = NetworkService(NetworkCache())
        self._plot_svc = PlottingService(self._canvas)
        self._setup_ui()
        self._connect_signals()

    def _on_plot_button_clicked(self):
        ports = self._parse_port_input()
        data = self._net_svc.get_param_matrix(self._current_file, self._param_type)
        self._plot_svc.plot_curve(...)
```

主窗口从 1 518 行压缩至 **≤ 600 行**。

---

### 3.2 拆解 sparam_core.py

将五个领域迁移到各自文件：

```
sparam_core.py (765 行)
    ↓
domain/algorithms/impedance.py   (enforce_nonzero_impedance, enforce_nonzero_z0)
domain/algorithms/se2diff.py     (SE2diff, SE2dq_dqs, SE2diff_port, merge_ports_multi)
domain/algorithms/ripple.py      (ripple_calc — 合并两版本为一个带参数的实现)
domain/algorithms/time_domain.py (compute_time_domain, _td_*, td_default_params, td_compat_check)
domain/port_parser.py            (parse_port_input — 合并两版本)
```

**合并 ripple_calc 重复**（当前两个函数差异只在是否绘图）：

```python
# 目标：单一函数，绘图为可选参数
def ripple_calc(
    ntwk: skrf.Network,
    ports: list[tuple[int, int]],
    method: FitMethod,
    plot_ax: Axes | None = None,   # None = 不绘图（测试场景）
) -> RippleResult:
    ...
```

---

### 3.3 引入枚举替代魔法字符串

**`domain/enums.py`**

```python
from enum import Enum, auto

class ParamType(Enum):
    S = "S参数"
    Y = "Y参数"
    Z = "Z参数"
    TIME_DOMAIN = "时域"

class DisplayMode(Enum):
    MAG_DB   = "幅度(dB)"
    PHASE    = "相位(°)"
    REAL     = "实部"
    IMAG     = "虚部"
    IMPEDANCE = "阻抗(Ω)"

class FitMethod(Enum):
    POLYNOMIAL = "多项式"
    IEEE_8023  = "IEEE 802.3-2022"
    SAVGOL     = "Savitzky-Golay"
```

---

### 3.4 对话框解耦：用回调/信号替代父引用

**现状（紧耦合）：**
```python
# dialogs/cascade.py 内部
result = do_cascade(...)
self.parent().register_network(name, result)   # 直接调用主窗口方法
self.parent().invalidate_file_cache(old_name)
```

**目标（依赖倒置）：**
```python
# dialogs/cascade.py
class CascadeDialog(QDialog):
    # 信号携带结果，主窗口连接处理
    cascade_done = pyqtSignal(str, object)  # (name, network)

    def _on_confirm(self):
        result = do_cascade(...)
        self.cascade_done.emit(new_name, result)
        self.accept()

# ui/main_window.py
dlg = CascadeDialog(networks, self)
dlg.cascade_done.connect(self._net_svc.register_network)
dlg.exec()
```

对话框不再持有主窗口引用，可以独立实例化和测试。

---

### 3.5 缓存层独立

**`infra/cache.py`**

```python
class NetworkCache:
    """基于文件指纹的 skrf.Network 缓存，支持 S/Y/Z 派生矩阵。"""

    def __init__(self, max_files: int = 50): ...
    def get(self, name: str) -> CacheEntry | None: ...
    def put(self, name: str, ntwk: skrf.Network, fingerprint: str): ...
    def invalidate(self, name: str): ...
    def fingerprint(self, path: str) -> str: ...  # mtime + size
```

从主窗口剥离后，缓存逻辑可以独立测试，还可以将来替换为 LRU 或磁盘缓存。

---

## 四、分阶段迁移策略

遵循**不停产原则**：每个阶段结束后应用仍可正常打包和运行。

### Phase 1 — 零风险清理（1～2 天）✅ 已完成

目标：减少技术债，不改变任何外部行为。

- [x] 在 `QS_domain/enums.py` 创建枚举（`ParamType`, `DisplayMode`, `FitMethod`）
- [x] 合并 `parse_port_input` / `parse_port_input1` 为单一函数（`QS_domain/port_parser.py`）
- [x] 合并 `ripple_calc` / `ripple_calc1`（`QS_domain/algorithms/ripple.py`）
- [x] 将重复的 matplotlib 字体配置提取到 `app_utils.configure_matplotlib()`
- [~] `sparam_core.py` 类型注解（部分完成，shim 层已加注解）

**验收标准**：`python -m pytest tests -q` → 75 passed ✅

---

### Phase 2 — 算法层分离（3～5 天）✅ 已完成

目标：`sparam_core.py` 内容迁移到 `QS_domain/algorithms/`，但对外接口不变。

- [x] 创建 `QS_domain/` 目录和各 `algorithms/*.py` 文件
- [x] `sparam_core.py` 改为 re-export shim，保留旧导入路径
- [x] 为迁移后的算法函数编写单元测试（`tests/domain/`，`tests/compat/`）
- [x] `QS_domain/algorithms/impedance.py` 拆分为纯函数：`has_zero_impedance()` + `replace_zero_impedance()`（无 Qt 依赖）
- [x] `QS_domain/algorithms/se2diff.py` 移除 Qt 依赖，改为抛出 `ValueError`

**验收标准**：`QS_domain/` 搜索不到 `PyQt6` ✅，单元测试全部通过 ✅

---

### Phase 3 — 服务层抽取（5～7 天）✅ 已完成

目标：从主窗口剥离 `NetworkService` 和 `NetworkCache`。

- [x] 实现 `QS_infra/cache.py`（`NetworkCache`，基于文件指纹）
- [x] 实现 `QS_services/network_service.py`（含 `NetworkLoadError` 异常，无 Qt）
- [x] 主窗口中用 `self._net_svc` 替代直接操作字典
- [x] `main_window.get_param_matrix()` 捕获 `NetworkLoadError`，统一回到 UI 层弹窗
- [~] 对话框逐步切换为信号/回调模式（已完成 `RippleFitDialog` 注入 network_service；`port_reduction`, `time_domain` 尚未迁移）

**当前行数**：`main_window.py` ≈ 1 390 行（目标 ≤ 800 行，尚未达到）

---

### Phase 3.5 — 显示配置统一（新增）✅ 已完成

目标：消除 `main_window.py` 和 `plotting_service.py` 双重维护的配置。

- [x] 新建 `QS_domain/display_config.py`，集中维护 `FACET_OPTIONS` + `DEFAULT_SCALES`
- [x] `main_window.py` 改为从 `display_config` 导入，删除本地副本
- [x] `QS_services/plotting_service.py` 从 `display_config` 导入 `DEFAULT_SCALES`

**验收标准**：`main_window.py` 不再定义 `_FACET_OPTIONS` / `_DEFAULT_SCALES` ✅

---

### Phase 4 — 绘图服务与主窗口瘦身（3～5 天）⬜ 未开始

目标：完成主窗口最终瘦身，实现 `PlottingService`。

- [ ] 实现 `QS_services/plotting_service.py` 中的 matplotlib 状态封装（`PlottingService` 类）
- [ ] 主窗口 `plot_s_parameters()` 等方法委托给 `PlottingService`
- [ ] 最终目标：`main_window.py` ≤ 1 000 行（下阶段里程碑），最终目标 ≤ 600 行

**验收标准**：所有绘图功能（多文件叠加、纹波拟合曲线、频段标注）正常工作。

---

### Phase 5 — 对话框解耦（持续推进）⬜ 试点完成

目标：对话框不再通过 `self.parent()` 直接访问主窗口方法。

- [x] `RippleFitDialog` — 注入 `network_service`，不再 `parent.get_network()` / `parent.get_param_matrix()`
- [x] `PortReductionDialog` — 注入 `network_service`，移除直接 `self.parent().get_network()` 调用
- [x] `PortMergeDialog` — 注入 `network_service`，更新 `check_and_set_port_names` 调用
- [x] `CascadeDialog` — 注入 `network_service`，更新 `check_and_set_port_names` 调用
- [x] `TimeDomainDialog` — 注入 `network_service` + `get_selected_files` 回调，移除数据层 parent() 调用
- [x] `app_utils.check_and_set_port_names` — 支持可选 `network_service` 参数，不再强依赖 `parent.get_network()`
- [ ] `se2diff` 对话框 — 调用 SE2diff 前检查零阻抗并提示用户（承接 domain 层的 ValueError）
- [ ] `freq_analysis.py` — 体量最大（~1 800 行），独立评估
- [ ] 最终：对话框正常路径不再调用 `self.parent().<任何方法>`

---

### Phase 6 — 测试覆盖与文档（持续）⬜

- [x] `tests/domain/` 覆盖端口解析、纹波计算
- [x] `tests/services/` 覆盖 `NetworkService` 核心接口
- [x] `tests/infra/` 覆盖 `NetworkCache`
- [x] `tests/compat/` 覆盖旧导入路径和纯函数行为
- [ ] 领域层（`QS_domain/`）单元测试覆盖率 ≥ 80%
- [ ] 服务层集成测试（使用真实 `.snp` 文件）
- [ ] 更新 `CLAUDE.md` 反映新架构
- [ ] 枚举在服务层边界开始接入（边界转换模式）

---

## 五、重构收益预测

| 指标 | 现状 | 目标 |
|------|------|------|
| `main_window.py` 行数 | 1 518 | ≤ 600 |
| 可独立测试的代码比例 | ~5% | ≥ 60% |
| 对话框到主窗口直接调用数 | 20+ | 0 |
| 魔法字符串数量 | 30+ | 0（全枚举） |
| 重复函数数量 | 4 | 0 |
| 单元测试数量 | 0 | ≥ 30 |

---

## 六、需要特别注意的风险点

### R1 — `enforce_nonzero_impedance` 含 QDialog

`sparam_core.py` 中该函数内部弹出一个 Qt 对话框，这是领域层唯一的 UI 依赖。
**处理方案**：将对话框逻辑移至调用方（`dialogs/port_reduction.py`），`enforce_nonzero_impedance` 改为纯函数，接收 `z0_override` 参数。

### R2 — matplotlib 后端敏感性

同时安装了 PyQt5/PyQt6，切勿在迁移过程中在新模块顶部调用 `matplotlib.use()`。
`PlottingService` 应在方法内部懒加载 pyplot（延续现有 `_get_pyplot()` 模式）。

### R3 — PyInstaller 打包路径

`resource_path()` 依赖 `sys._MEIPASS`，迁移到 `infra/resource_path.py` 后需确保 `.spec` 文件中路径配置一致。

### R4 — runtime_services 不动

`trial_manager.py` 等运维服务与业务逻辑无耦合，且结构相对独立，本次重构**不涉及**，避免引入不必要风险。

---

## 七、不在本次范围内的事项

以下是可能的改进方向，但超出当前重构范围，不建议同步推进：

- 切换到 PySide6（许可证差异，需独立评估）
- 引入 async/await 处理大文件加载
- 插件化架构（支持第三方分析模块）
- 从 PyInstaller 迁移到其他打包工具

---

*本文档应随重构进度持续更新，每完成一个 Phase 后在对应 checklist 打勾并记录实际耗时。*
