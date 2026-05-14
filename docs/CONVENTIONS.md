# CONVENTIONS — 项目硬约束与运行规范

> Tier 1 文档：按需加载。本文档收录"会被代码评审或测试套件直接拒绝的"约定。
> 真正的硬约束已在 `AGENT_GUIDE.md` §三 中以一句话列出；本文档把每条展开成可执行细节。

---

## §Qt / matplotlib

- **禁止在模块级调用 `matplotlib.use(...)`**。
  本机同时安装 PyQt5 + PyQt6，若强制 `Qt5Agg` 后端，频域分析对话框（`QS_dialogs/freq_analysis.py`）会闪退。
  让 matplotlib 自动选择后端，预期值为 `QtAgg`（→ `Qt6Agg`）。

- **统一字体配置入口**：`app_utils.configure_matplotlib()`，幂等，可在任意位置调用。
  Windows 用 `SimHei`，Linux 用 `WenQuanYi Zen Hei`；并设 `axes.unicode_minus = False`。
  新写的脚本/对话框**不要**重新写一遍字体配置，调 `configure_matplotlib()` 即可。

- **对话框中嵌入 matplotlib**：直接 `from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg`，不要 import `backend_qt5agg`。

- **入口顺序**：参考 `Quick_Sparam_B.py`——先 `os.environ.setdefault("SKRF_PLOT_ENV", "none")` 抑制 skrf 的默认绘图行为，再创建 `QApplication`，再 `configure_matplotlib()`，最后 import 主窗口。

---

## §中文 locale

- 所有 UI 字符串、错误消息、注释一律使用**简体中文**。
- 跨层流通的参数类型字符串：`'S参数' / 'Y参数' / 'Z参数' / '时域'`。改名要同步：
  - `QS_domain/enums.py::ParamType`
  - `QS_domain/display_config.py::FACET_OPTIONS`
  - `QS_services/network_service.py::get_param_matrix` 的 attr_map
  - `QS_infra/cache.py::_PARAM_ATTRS`
- 数据切面字符串（`'幅度(dB)'`、`'阻抗(mΩ)'`...）的规范定义在 `QS_domain/enums.py::DisplayMode`；UI 下拉框从 `FACET_OPTIONS` 读取。

---

## §分层依赖（违反即视为回归）

- `QS_domain/` 与 `QS_services/` 内**禁止 `import PyQt6`**——测试套件应捕获。
- `app_utils.py::check_and_set_port_names` 在函数体内**懒导入** `QS_dialogs.port_selector / port_name`，避免循环依赖。新增类似工具时沿用此模式。
- `sparam_core.py` 是 shim：新算法直接放进 `QS_domain/algorithms/`，仅当需要保护旧 import 路径时才在 shim 末尾追加 re-export。
- `QS_runtime_services/` 是独立子系统（试用/版本/反馈），未经用户授权不要改。

---

## §测试

```bash
python -m pytest tests/ -q      # 提交前必跑（~75 项）
```

- 目录划分：`tests/domain/`、`tests/services/`、`tests/infra/`、`tests/compat/`。
- `tests/compat/test_sparam_core.py` 保护向后兼容入口，若你"清理" shim 必然挂这条。
- 新增 domain 算法：建议在 `tests/domain/` 增同名 `test_*.py`，覆盖正常路径 + 异常路径。
- `dev_scripts/` 内的 `.py` 是**非 pytest 冒烟脚本**，不会被自动跑，需要手动执行。

---

## §打包 / 资源路径

- 打包工具：`auto-py-to-exe` 或直接 `pyinstaller Quick_Sparam_install.spec`（精简版）/ `pyinstaller Quick_Sparam_B.py`（完整版）。
- 任何需要在打包后访问的资源（图标、模板、文档），必须用 `app_utils.resource_path("relative/path")` 包装，否则在冻结环境下找不到（依赖 `sys._MEIPASS`）。
- 资源放在仓库根的 `resources/`（图标如 `resources/ico_test.ico`）或对应目录；通过 PyInstaller spec 的 `datas` 加入即可。
- 入口是统一的 `Quick_Sparam_B.py`，三组旗标互不冲突：
  - `--dev`：开发预设（预填一组本机文件/端口），仅命令行生效，冻结后不触发。
  - `--limited` 或环境变量 `QS_LIMITED=1`：精简版（关时域 + 跳过 usage profile）。
  - PyInstaller 精简版打包通过 `Quick_Sparam_install.spec` 的 `runtime_hooks=['pyinstaller_hooks/set_limited_env.py']` 在 exe 启动时强制 `QS_LIMITED=1`。
- `pyinstaller_hooks/` 目录必须随发布包一起进 PyInstaller spec，否则精简版 exe 启动会退回完整版。

---

## §端口编号约定

- **跨层接口**统一 1-based：`ripple_calc(network, p1, p2, ...)`、`SE2diff_port(network, diff_list=[1,2,3,4])`、UI 输入框、日志输出。
- **算法内部**自由使用 0-based（`merge_ports_multi`、`SE2diff` 内部都做 `-1` 转换）。
- `QS_domain/port_parser.parse_port_input` 既支持端口（int）也支持频率（float），由 `type` 参数区分。

---

## §提交规范

- 提交信息**简体中文**，与历史风格一致（参考 `git log --oneline`）。
- 一次提交只做一件事；架构变更和功能变更分开提交。
- 公共接口变更（`QS_services` / `QS_domain` 的 public 函数签名、`QS_infra.cache.NetworkCache` 的方法名）需同步：
  - 更新 `docs/INTERFACES.md` 对应章节
  - 跑 `tests/compat/` 确认没破坏 shim
- 提交前自检：`pytest tests/ -q` 通过 + 无 PyQt6 在 `QS_domain/` 或 `QS_services/` 中。

---

## §不要做的事

- 不要把任务清单、PR 描述、会话上下文写进任何 `docs/*.md`（用 task list / commit message / PR body）。
- 不要"顺手"重构。本仓库正处于分层重构中后期，请只完成被要求的改动，不要把 1216 行的 `main_window.py` 一次性拆完。
- 不要给 `QS_runtime_services/` 加测试或重构（属于独立子系统）。
- 不要扩张 `sparam_core.py` shim 的逻辑——它只能做 re-export 和最小 UI 翻译。
