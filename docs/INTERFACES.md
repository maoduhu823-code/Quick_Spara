# INTERFACES — 关键公共接口速查

> Tier 1 文档：按需加载。本文档**只列对外接口签名 + 一行说明**，不复制实现。
> 签名以代码为准；如果有出入，**以代码为准**，并修正本文。
>
> 看完本文你应该可以：(a) 知道每层暴露什么、(b) 决定要不要打开源文件继续读细节。

---

## §domain — `QS_domain/*`

### `QS_domain/enums.py`
```python
class ParamType(Enum):     # S='S参数' · Y='Y参数' · Z='Z参数' · TIME_DOMAIN='时域'
class DisplayMode(Enum):   # MAG_DB / MAG_ABS / PHASE_DEG / ... / TDR / STEP / IMPULSE / PULSE
class FitMethod(Enum):     # POLYNOMIAL='n次多项式' · IEEE_8023 · SAVGOL='平滑函数'
```

### `QS_domain/display_config.py`
```python
FACET_OPTIONS: dict[str, list[str]]                 # 参数类型 → 可选数据切面
DEFAULT_SCALES: dict[tuple[str, str], tuple[str, str]]  # (param_type, facet) → (x_scale, y_scale)
```

### `QS_domain/port_parser.py`
```python
def parse_port_input(input_str: str, type: str = 'port') -> list
# type='port' → list[int]；type='freq' → list[float]
# 支持: "1:5" · "1:2:5" · "[1,3,5]" · "1 3 5" · 全角逗号
# 失败抛 ValueError；UI 包装在 sparam_core.parse_port_input
```

### `QS_domain/algorithms/impedance.py`
```python
def has_zero_impedance(network) -> bool
def replace_zero_impedance(network, z0: float) -> None        # 全部端口替换为 z0
def enforce_nonzero_z0(network_ori, filepath: str) -> None    # 读 #-头行参考阻抗自动修正
```

### `QS_domain/algorithms/ripple.py`
```python
def ripple_calc(network, p1, p2, start_freqG, stop_freqG,
                data_mode, method, fit_params, s_params=None) -> dict
# data_mode: 幅度 (dB) / 幅度 (abs) / 相位 (度|rad) / unwrap相位 (度|rad) / 群延迟 (fs)
# method:    n次多项式 | IEEE_std_802.3-2022 | 平滑函数
# fit_params 依 method 不同:
#   n次多项式 → {'order': int}
#   平滑函数  → {'window_length': int, 'polyorder': int}
#   IEEE_8023 → {}
# return: label / freqG_range / s_param_range / fitted_curve / residuals
#       / max_ripple / max_ripple_freqG / max_ripple_index / formula
```

### `QS_domain/algorithms/se2diff.py`
```python
def SE2diff(network_ori, port_mode='inside', output_mode='sdd_only',
            z0_diff=[100, 100]) -> rf.Network
# port_mode: 'inline' | 'inside' | list[int]（自定义端口序列，1-based）
# output_mode: 'sdd_only'（仅差分子网）| 'full'（差分+共模混合）

def SE2dq_dqs(network_ori, line_list, port_mode='inside',
              z0_diff=[100, 100]) -> rf.Network
# line_list: 差分对的"线编号"列表（1-based）

def SE2diff_port(network_ori, diff_list, z0_diff=100.0,
                 output_mode='sdd_only') -> rf.Network
# diff_list: 差分端口编号列表（成对，1-based）
# 任一函数遇到零阻抗端口直接抛 ValueError，要求 UI 层先修正
```

### `QS_domain/algorithms/time_domain.py`
```python
def td_default_params(network) -> dict
# 返回 tr_ps / dt_ps / n_points / fmax_GHz / df_GHz / T_total_ps / dt_nyq_ps / N_f_total

def td_compat_check(network, tr_ps, dt_ps, n_points) -> dict
# 返回 {"tr": ok|warn|error, "dt": ..., "n": ..., "messages": [...]}

def compute_time_domain(network, p1, p2, waveform='TDR',
                        tr_ps=None, dt_ps=None, n_points=None,
                        z0=50.0, pulse_width_ps=None,
                        window_type='gaussian', method='legacy',
                        s_params=None) -> dict
# waveform: 'TDR' | 'impulse' | 'step' | 'pulse'
# window_type: 'gaussian' | 'rect' | 'hanning' | 'hamming' | 'blackman'
# method: 'legacy' | 'channel_analyse'
# return: time_ps / y_data / label / y_label / compat_status / impulse_h_t / dt_s

def suggest_time_window(h_t, dt_s, waveform='impulse',
                        threshold_factor=0.01, left_pad_frac=0.1,
                        right_pad_factor_by_wf=None) -> (float, float)
# 用冲激响应包络（>threshold_factor·peak）估计活动区间，
# 左侧 pad left_pad_frac×width，右侧按 waveform 类型 pad（impulse 0.3 / pulse 0.5 / step·TDR 1.0）
# 返回 (t_lo_s, t_hi_s)；h_t 空或全零退化为 (0, n·dt)
```

### `QS_domain/algorithms/port_merge.py`
```python
def merge_ports_multi(ntw, merge_groups: list[list[int]],
                      z0_list: list[float], y_orig=None) -> rf.Network
# merge_groups 内部用 0-based 端口索引；输出端口序：保留端口 + 各合并组
# 新端口命名: "Merge_port_<1-based索引用_分隔>"
```

### `QS_domain/algorithms/topology_detect.py`
```python
@dataclass
class ChannelInfo:
    ports: list[int]              # 1-based 端口号
    tx: int | None                # 低序号端口
    rxs: list[int]                # 仅包含高序号端口
    s_value: complex | None       # 识别频点上的 S(低序号, 高序号)
    z_value: complex | None       # 识别频点上的 Z(低序号, 高序号)
    topology: str                 # 当前固定为 "p2p"

@dataclass
class TopologyReport:
    n_ports: int
    band_ghz: tuple[float, float]
    low_freq_ghz: float
    y_threshold_siemens: float
    s_threshold_db: float
    channels: list[ChannelInfo]
    isolated_ports: list[int]

def detect_topology(network, low_freq_ghz=0.1, band_ghz=None,
                    y_threshold_siemens=5e-4, s_threshold_db=-25.0,
                    delay_tolerance_ns=0.1) -> TopologyReport
# 当前仅识别 1 驱 1：低频 S→Y 后，每个端口选 |Y_ij| 最大的另一端口；
# 互为最强关系才输出为联通端口对（小序号 -> 大序号）。
# low_freq_ghz 使用最接近输入频点的实际频点。
# band_ghz / y_threshold_siemens / s_threshold_db / delay_tolerance_ns 为兼容参数，本版不参与判别。

def format_report(report: TopologyReport, file_label: str = "") -> str
```

---

## §services — `QS_services/*`

### `QS_services/network_service.py`
```python
class NetworkLoadError(Exception): ...

class NetworkService:
    def __init__(self, cache: NetworkCache | None = None)
    debug: bool                                            # property，代理 cache.debug
    s_data: dict[str, rf.Network]                          # property，原始字典引用
    def get_network(file_name) -> rf.Network               # 自动指纹失效 + enforce_nonzero_z0
    def register_network(file_name, network) -> None       # 注册内存生成的 Network（无指纹）
    def get_param_matrix(file_name, param_type) -> ndarray # param_type ∈ {'S参数','Y参数','Z参数'}
    def get_s(file_name) -> ndarray
    def get_y(file_name) -> ndarray
    def get_z(file_name) -> ndarray
    def invalidate_file_cache(file_name, include_network=False) -> None
    def clear_all_cache() -> None
```

### `QS_services/plotting_service.py`
```python
def compute_param_data(param: ndarray, facet: str, freqG: ndarray) -> (ndarray, str)
# facet 见 DisplayMode；返回 (y_data, y_label)

def get_axis_labels(param_type, facet) -> (str, str)       # 返回 (x_label, y_label)
def get_default_scales(param_type, facet) -> (str, str)    # 读 DEFAULT_SCALES，默认 ('线性','线性')
```

---

## §infra — `QS_infra/*`

### `QS_infra/cache.py`
```python
class NetworkCache:
    debug: bool

    @staticmethod
    def compute_fingerprint(file_name) -> tuple | None     # (abspath, st_mtime_ns, st_size) 或 None

    def has_network(key) -> bool
    def get_raw_networks() -> dict[str, rf.Network]        # 内部字典引用
    def get_network(key) -> rf.Network | None              # 命中且未失效才返回
    def put_network(key, network, fingerprint=None) -> None
    def register_network(key, network) -> None             # 内存对象，fingerprint=None

    def get_param(key, param_type) -> ndarray | None       # param_type ∈ {'S参数','Y参数','Z参数'}
    def put_param(key, param_type, matrix) -> None

    def invalidate(key, include_network=False) -> None
    def clear_all() -> None
```

### `QS_infra/resource_path.py`
```python
def resource_path(relative_path: str) -> str               # 兼容 PyInstaller _MEIPASS
```

---

## §main_window — 对话框依赖的入口

`SParameterViewer_MainWin(QWidget)` 对外（被 `QS_dialogs/*` 使用）的接口：

```python
# 数据访问（薄包装到 NetworkService）
get_network(file_name) -> rf.Network
get_param_matrix(file_name, param_type) -> ndarray | None
get_s(file_name) / get_y(file_name) / get_z(file_name) -> ndarray | None
register_network(file_name, network) -> None
invalidate_file_cache(file_name, include_network=False) -> None
clear_all_cache() -> None
s_data  # property → dict[str, rf.Network]

# 文件列表 widget 操作
get_file_key_from_item(item) / get_selected_file_keys() / get_all_file_keys()
add_file_list_item(file_key) / refresh_file_list_display()
add_unique_filename(new_file_name) -> str
```

> 写新对话框时**不要**新增对主窗口的反向引用——通过构造参数注入 `NetworkService` 或所需数据。`QS_dialogs/ripple.py` 是已重构的样板。

---

## §app_utils — Qt 工具

```python
show_error(parent, context_message="") -> None
configure_matplotlib() -> None                              # 幂等，可重复调用
resource_path(relative_path) -> str                         # 包装 QS_infra.resource_path
freq_band_data_extract(mark_freqGs, freqG, y_data, ax, worst_mode='max') -> (list, list)
plot_main_curves(results_data, data_mode) -> None
plot_residuals(results_data, data_mode) -> None
check_and_set_port_names(parent, file_list, network_service=None) -> list[int] | None
```

---

## §sparam_core（兼容 shim，新代码勿用）

re-export 自 `QS_domain/algorithms/*` 与 `QS_domain/port_parser`：
`has_zero_impedance` · `replace_zero_impedance` · `enforce_nonzero_z0` ·
`SE2diff` · `SE2dq_dqs` · `SE2diff_port` ·
`ripple_calc` · `merge_ports_multi` ·
`td_default_params` · `td_compat_check` · `compute_time_domain` ·
`parse_port_input`（**唯一带 UI 包装**：把 ValueError 翻译为 QMessageBox 并返回 None）
