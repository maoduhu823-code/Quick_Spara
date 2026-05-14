# Quick_Sparam 架构重构验收评审

> 日期：2026-05-12
> 对象：`docs/architecture_refactor_plan.md` 对应的 Claude Code 重构结果
> 结论：建议保留本次重构成果，但将其标记为“分层重构第一阶段完成”，不要认定为完整架构重构完成。

---

## 一、总体结论

这次重构方向正确，且已经产生了实际收益：`sparam_core.py` 被压缩为向后兼容的导出层，算法代码开始进入 `domain/`，缓存和参数读取开始进入 `services/` / `infra/`，同时补充了基础单元测试。

从工程风险角度看，这次重构采用了比较稳妥的方式：保留旧导入路径，不要求一次性改完所有调用方，降低了对现有 UI 和对话框功能的破坏概率。

但从目标架构角度看，当前落地仍处在中间态。计划中提出的“领域层无 UI 依赖”“服务层无 Qt 依赖”“主窗口瘦身到 600 行以内”“对话框与主窗口解耦”等目标尚未完成。因此，本次重构更适合定义为 Phase 1 和 Phase 2 的主要成果，加上 Phase 3/4 的局部尝试。

---

## 二、已达成效果

### 2.1 `sparam_core.py` 已变成兼容 shim

`sparam_core.py` 当前主要负责从新模块重新导出旧函数，例如：

- `domain.algorithms.ripple.ripple_calc`
- `domain.algorithms.se2diff.SE2diff`
- `domain.algorithms.time_domain.compute_time_domain`
- `domain.port_parser.parse_port_input`

这意味着旧代码仍可继续使用：

```python
from sparam_core import ripple_calc
```

而真实实现已经迁移到新的领域模块中。这是一种合理的过渡方式，可以避免一次重构牵动所有 UI、对话框和测试入口。

### 2.2 算法层拆分已经启动

当前已新增：

- `domain/port_parser.py`
- `domain/algorithms/ripple.py`
- `domain/algorithms/se2diff.py`
- `domain/algorithms/time_domain.py`
- `domain/algorithms/port_merge.py`
- `domain/algorithms/impedance.py`

其中端口解析、纹波计算、时域计算等逻辑已经具备单独测试的基础。

### 2.3 缓存与参数读取开始从主窗口剥离

主窗口已经不再直接维护原来的多组缓存字典，而是通过 `NetworkService` 委托：

- `get_network()`
- `register_network()`
- `get_param_matrix()`
- `invalidate_file_cache()`
- `clear_all_cache()`

这一步对降低 `main_window.py` 的职责复杂度有帮助。

### 2.4 已补充基础测试

新增测试覆盖了：

- 端口/频率字符串解析
- 纹波拟合核心结果
- 绘图数据转换逻辑

已验证：

```bash
python -m pytest tests -q
```

结果为：

```text
45 passed
```

同时，核心 Python 文件语法编译通过，主窗口 offscreen 实例化烟测未发现明显断裂。

---

## 三、主要不足

### 3.1 服务层仍然依赖 Qt

计划中定义 `services/` 为应用层，原则上“不含 Qt，不直接操作 UI”。但当前 `services/network_service.py` 仍然引入了：

```python
from PyQt6.QtWidgets import QMessageBox
```

并在参数读取失败时直接弹窗。

这会带来几个问题：

- `NetworkService` 仍然不能作为纯业务服务独立复用。
- 单元测试需要规避 Qt 弹窗路径。
- 未来如果想做命令行批处理、自动化测试或后台任务，会被 UI 依赖卡住。
- 异常处理策略分散，服务层既负责读数据，又负责决定如何提示用户。

### 3.2 领域层仍然存在 UI 依赖

`domain/algorithms/impedance.py` 中的 `enforce_nonzero_impedance()` 仍然创建 `QApplication`、`QDialog`、`QMessageBox`。

这说明该模块虽然被放进了 `domain/algorithms/`，但它还不是纯领域算法。当前只是“文件位置迁移”，还没有完成职责迁移。

这点风险比较高，因为领域层一旦混入 UI，后续测试、复用和批处理都会受到影响。

### 3.3 主窗口瘦身有限

`main_window.py` 从原来的约 1500 行下降到约 1390 行，说明确实有部分逻辑被抽离，但主窗口仍然是主要复杂度中心。

当前主窗口仍然承担：

- UI 布局
- 文件列表状态
- 绘图控制
- 端口输入解析调度
- 时域分析调度
- 各对话框创建与结果接收
- 输出框重定向
- 部分数据转换和标签拼装

这还没有达到计划中“表现层只负责布局和事件路由”的目标。

### 3.4 枚举已创建但未真正接入

`domain/enums.py` 中已经定义：

- `ParamType`
- `DisplayMode`
- `FitMethod`

但主流程仍大量使用裸字符串，例如：

- `'S参数'`
- `'Y参数'`
- `'Z参数'`
- `'幅度(dB)'`
- `'阻抗(mΩ)'`

因此，目前枚举只是“准备好了”，还没有实际降低魔法字符串风险。

### 3.5 显示模式和默认坐标缩放存在重复定义

`main_window.py` 中仍有 `_FACET_OPTIONS` 和 `_DEFAULT_SCALES`。同时，`services/plotting_service.py` 中也有 `DEFAULT_SCALES` 和 `get_default_scales()`。

这会形成两个事实来源：

- UI 控件下拉选项来自 `main_window.py`
- 默认坐标缩放可能来自 `main_window.py` 或 `plotting_service.py`

未来新增显示模式时，容易出现“UI 能选，但绘图服务不认识”或“服务支持，但 UI 没有暴露”的问题。

### 3.6 对话框与主窗口仍然高度耦合

多个对话框仍通过 `self.parent()` 访问主窗口能力，例如：

- 获取网络对象
- 获取端口名
- 注册新网络
- 读取主窗口当前状态

这说明计划中的“用信号/回调替代父窗口直接调用”尚未真正启动。

当前模式短期可用，但长期会导致：

- 对话框难以单独测试。
- 对话框只能挂在特定主窗口下使用。
- 主窗口接口越来越像“全局服务容器”。
- 新功能容易继续把业务逻辑塞回 UI 层。

### 3.7 计划文档未同步实际进度

`docs/architecture_refactor_plan.md` 中 checklist 仍全部保持未勾选状态，但实际代码已经完成了部分任务。

这会降低文档可信度，也会让下一轮重构难以判断“哪些已完成、哪些只是计划”。

### 3.8 本地工具配置和临时产物需要提交前清理

当前重构后存在一些不适合直接提交的内容：

- `.claude/settings.local.json`：本地工具权限配置，不建议混入源码提交。
- `build/`、`dist/`：打包产物，不建议入库。
- `importtime_*.txt`：性能分析临时日志，不建议入库。
- `__pycache__/`、`.pytest_cache/`：运行缓存，应由 `.gitignore` 忽略。

---

## 四、细化改进建议

### 建议 1：先把服务层从 Qt 弹窗中解耦

目标：`services/` 不再 import PyQt6。

推荐做法：

1. 新增业务异常类，例如：

```python
class NetworkLoadError(Exception):
    pass
```

2. `NetworkService.get_param_matrix()` 中遇到读取失败时，不弹窗，只抛异常或返回结构化结果。

3. 主窗口调用服务层时捕获异常，再决定是否调用 `QMessageBox.warning()`。

示意：

```python
try:
    matrix = self._net_svc.get_param_matrix(file_name, param_type)
except NetworkLoadError as exc:
    QMessageBox.warning(self, "加载错误", str(exc))
    return None
```

收益：

- 服务层可以脱离 Qt 测试。
- 错误展示统一回到 UI 层。
- 未来批处理或自动化任务可以复用 `NetworkService`。

验收标准：

- `services/` 中搜索不到 `PyQt6`。
- `NetworkService` 的失败路径有单元测试。

### 建议 2：把阻抗弹窗从领域层移回 UI 层

目标：`domain/algorithms/impedance.py` 只做数据修正，不创建任何 Qt 控件。

推荐拆成两个函数：

```python
def has_zero_impedance(network) -> bool:
    ...

def replace_zero_impedance(network, z0: float) -> None:
    ...
```

UI 层负责：

1. 调用 `has_zero_impedance()` 检查是否需要用户输入。
2. 弹出 `Z0EditDialog` 或现有阻抗输入框。
3. 用户确认后调用 `replace_zero_impedance()`。

这样可以把“是否弹窗、弹什么文案、用户取消后如何处理”留给 UI 层，把“如何修改 network.z0”留给领域层。

验收标准：

- `domain/` 中搜索不到 `PyQt6`。
- 阻抗修正逻辑有不依赖 QApplication 的单元测试。

### 建议 3：统一显示模式、参数类型和默认缩放配置

目标：避免 `main_window.py` 和 `services/plotting_service.py` 两处维护同一类配置。

推荐新建或扩展一个配置模块，例如：

```python
domain/display_config.py
```

集中维护：

- 参数类型列表
- 每种参数类型支持的显示模式
- 每种显示模式的默认坐标缩放
- 显示模式对应的数据转换函数

主窗口只从这个模块读取 UI 下拉选项。绘图服务也从这个模块读取默认缩放。

收益：

- 新增显示模式只改一个地方。
- UI 和绘图逻辑不会失配。
- 后续可逐步用 `ParamType` / `DisplayMode` 替代裸字符串。

验收标准：

- `main_window.py` 不再定义 `_FACET_OPTIONS` 和 `_DEFAULT_SCALES`。
- `services/plotting_service.py` 与 UI 使用同一份配置来源。

### 建议 4：枚举先在边界层使用，不要一次性全量替换

裸字符串一次性全替换风险较高，因为 UI 下拉框、历史文案和旧函数都依赖中文字符串。

建议采用渐进式策略：

1. UI 控件仍显示中文 `.value`。
2. 进入服务层时转换为枚举。
3. 服务层内部尽量使用枚举。
4. 返回 UI 层时再转成 `.value`。

示意：

```python
param_type = ParamType(self.param_type_combo.currentText())
matrix = self._net_svc.get_param_matrix(file_name, param_type)
```

`NetworkService` 内部可以接受 `ParamType | str`，过渡期保持兼容。

验收标准：

- 新代码优先使用枚举。
- 旧 UI 文案不变化。
- 单元测试覆盖字符串和枚举两种输入。

### 建议 5：对话框解耦先从新增/生成网络类功能开始

不建议一次性重写所有对话框。可以先挑最容易验证的场景：

- 端口合并
- 级联
- 差分转换

这些对话框的共同特点是：输入若干网络，输出一个新网络。适合改成信号或回调。

推荐目标接口：

```python
dialog.network_created.connect(self.register_network)
```

对话框内部只负责计算和发出结果，不直接调用：

```python
self.parent().register_network(...)
```

收益：

- 对话框可以独立测试。
- 主窗口注册网络的逻辑集中。
- 未来增加批处理入口时，可以复用相同计算流程。

验收标准：

- 至少一个对话框不再调用 `self.parent().register_network()`。
- 对话框可以在测试中构造并触发核心逻辑。

### 建议 6：主窗口继续按功能区拆分，而不是只按文件拆分

主窗口现在仍然很大。下一步建议按功能区拆出辅助类或 mixin，但要避免制造过多抽象。

优先拆：

1. 文件列表管理：选中、显示完整路径/文件名、去重命名。
2. 绘图参数读取：端口输入、参数类型、显示模式、坐标缩放。
3. 绘图执行：从网络取数据、转换 y_data、更新 canvas。
4. 启动任务：版本检测、问卷弹出、试用检查。

不建议立刻迁移成全新的 `ui/main_window.py` 路径，因为这会影响入口、PyInstaller 和旧引用。可以先在现有 `main_window.py` 周边引入小模块，等稳定后再移动 UI 目录。

验收标准：

- `main_window.py` 降到 1000 行以内作为下一阶段目标。
- 每次拆分后都能运行主窗口烟测。
- 不引入新的循环 import。

### 建议 7：补一组服务层和兼容层测试

当前测试集中在端口解析、纹波、绘图数据转换。下一步建议补：

- `sparam_core.py` 旧导入路径仍可用。
- `NetworkCache` 指纹变化后会失效。
- `NetworkService` 注册内存网络后能读取 S/Y/Z。
- `resource_path()` 在普通环境下返回正确路径。
- `parse_port_input()` 的 UI 包装层遇到错误返回 None。

其中 `parse_port_input()` 的 UI 包装层测试可以用 monkeypatch 替换 `QMessageBox.warning`，避免真实弹窗。

验收标准：

- `tests/services/` 覆盖 `NetworkService`。
- `tests/infra/` 覆盖 `NetworkCache`。
- `tests/compat/` 覆盖旧导入路径。

### 建议 8：更新计划文档的 checklist

建议在 `docs/architecture_refactor_plan.md` 中增加“实际进度”或直接勾选已完成项。

可以采用三种状态：

- `[x]` 已完成
- `[~]` 部分完成
- `[ ]` 未开始

例如：

- `[x] 创建 domain/ 目录和 algorithms/*.py`
- `[x] sparam_core.py 改为 re-export shim`
- `[~] 创建枚举，但尚未全面接入`
- `[~] 实现 services/network_service.py，但仍有 Qt 依赖`
- `[ ] 对话框逐步切换为信号/回调模式`

这样后续继续重构时，不会重复做已经完成的事。

### 建议 9：提交前清理或忽略临时产物

建议补充 `.gitignore`：

```gitignore
build/
dist/
*.spec~
importtime_*.txt
.pytest_cache/
```

是否忽略 `.spec` 需要谨慎：如果 `.spec` 是正式打包配置，应提交；如果只是本机临时生成，则不提交。

`.claude/settings.local.json` 建议不提交，除非你明确希望团队共享 Claude Code 的本地权限配置。

验收标准：

- `git status --short` 中不再出现打包目录和运行缓存。
- 本次重构提交只包含源码、测试、文档和必要资源。

---

## 五、建议的下一阶段顺序

推荐下一轮不要继续大范围搬文件，而是按风险递减顺序处理：

1. 清理提交范围：排除本地工具配置、打包产物、缓存文件。
2. 服务层去 Qt：移除 `services/network_service.py` 中的 `QMessageBox`。
3. 领域层去 Qt：重构 `domain/algorithms/impedance.py`。
4. 统一显示配置：合并 `_FACET_OPTIONS`、`_DEFAULT_SCALES`、`DEFAULT_SCALES`。
5. 补服务层测试：覆盖 `NetworkService` 和 `NetworkCache`。
6. 选择一个对话框试点信号/回调解耦。
7. 再继续主窗口瘦身。

这样做的好处是：每一步都能独立验收，并且每一步都能减少后续重构的不确定性。

---

## 六、下一阶段验收标准建议

下一轮重构完成后，建议至少满足以下条件：

- `python -m pytest tests -q` 全部通过。
- `python -m py_compile` 覆盖入口文件、`domain/`、`services/`、`infra/`。
- `services/` 中不再出现 `PyQt6`。
- `domain/` 中除明确的兼容包装外不再出现 `PyQt6`。
- `main_window.py` 行数下降到 1000 行以内。
- 至少一个对话框完成信号/回调解耦。
- `docs/architecture_refactor_plan.md` checklist 与实际进度同步。
- `git status --short` 中没有 `build/`、`dist/`、`importtime_*.txt` 等临时产物。

---

## 七、是否建议提交当前重构

建议提交，但提交说明要准确。

推荐提交名：

```text
架构分层重构第一阶段存档
```

不建议使用：

```text
完成架构重构
```

因为当前结果仍是中间态，后续还需要继续去 Qt 依赖、消除重复配置、解耦对话框和瘦身主窗口。
