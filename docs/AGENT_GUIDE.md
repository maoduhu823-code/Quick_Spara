# AGENT_GUIDE — 多智能体协作入口

> 所有 AI 助手（Claude Code / Codex / Cursor / Aider 等）共用此文档。
> `CLAUDE.md` 与 `AGENTS.md` 仅作为指针指向本文件，正文不再各自维护。
>
> 设计目标：让任意智能体在不加载历史/专项文档的前提下，仅凭本文 (~120 行) 即可：
> (a) 理解项目分层、(b) 知道硬约束、(c) 知道按当前任务该再读哪份 Tier 1 文档。

---

## 一、项目一句话定位

Quick_Sparam 是基于 **PyQt6** 的 RF S 参数（Touchstone `.snp`）查看与分析桌面工具，由"封装SIPI开发部"维护。统一入口 `Quick_Sparam_B.py`（生产空白启动，加 `--dev` 走本地调试预设），使用 PyInstaller 打包为单 exe 分发。

## 二、分层概览（最少必读）

```
Quick_Sparam_B.py                   # 应用入口（无参=生产，--dev=本地调试预设）
main_window.py                      # 主窗口（瘦身中，仍 ~1216 行）
app_utils.py                        # Qt 工具：错误弹窗、字体配置、绘图辅助
sparam_core.py                      # 向后兼容 shim — 不要在新代码里 import

QS_domain/                          # 领域层 — 纯 Python，禁止 PyQt6
QS_services/                        # 应用服务层 — 禁止 PyQt6
QS_infra/                           # 基础设施（缓存、资源路径）
QS_dialogs/                         # UI 对话框（Qt）
QS_runtime_services/                # 试用/版本/反馈（独立子系统，不要改动）
samples/    .snp 样本    tests/    pytest 套件    dev_scripts/    冒烟脚本
```

**依赖方向**（任何 PR 违反即视为回归）：

```
QS_dialogs  ─┐
main_window ─┼─→ QS_services ─→ QS_domain ─→ QS_infra
app_utils   ─┘
```

## 三、硬约束（违反即失败）

1. **`QS_domain/` 与 `QS_services/` 内禁止 `import PyQt6`**（测试套件会捕获）
2. **不要在模块级调用 `matplotlib.use()`**——本机同时装了 PyQt5 与 PyQt6，强制 `Qt5Agg` 会导致频域分析对话框闪退。让 matplotlib 自动选 `QtAgg`。
3. **所有 UI 字符串使用简体中文**；Windows 字体 `SimHei`，Linux 字体 `WenQuanYi Zen Hei`，并设 `axes.unicode_minus = False`。
4. **`sparam_core.py` 是 shim**——新增算法直接放进 `QS_domain/algorithms/`，新增旧 import 的兼容入口可在 shim 末尾添加 re-export。
5. **提交前必须跑 `python -m pytest tests/ -q`**；测试目录约 75 项，覆盖 domain / services / infra / compat 四层。
6. **`QS_runtime_services/` 是独立子系统**（试用许可、版本管理、反馈聚合），未经用户授权不要改动。
7. **不要主动跑全盘 UI 烟测**（`dev_scripts/ui_smoke/run_all.py` 及单独的 `cases_*.py`）；除非用户明确要求，否则只跑 `pytest tests/`。烟测耗时较长且会弹/关 matplotlib 窗口，应由用户决定何时触发。

## 四、任务路由 — 按需加载 Tier 1 文档

| 任务类型 | 先读 | 再视情况读 |
|---------|------|-----------|
| 修算法 / 纯逻辑 | `ARCHITECTURE.md` §QS_domain | `INTERFACES.md` §domain |
| 改对话框 / UI 行为 | `ARCHITECTURE.md` §QS_dialogs + §main_window | `CONVENTIONS.md` §Qt |
| 改服务层（缓存、参数读取） | `INTERFACES.md` §services | `ARCHITECTURE.md` §QS_services + §QS_infra |
| 加 / 改测试 | `CONVENTIONS.md` §测试 | `INTERFACES.md`（理解被测函数签名）|
| 生成 HTML 使用指南 | `HTML_GUIDE_SKILL.md` | — |
| 想了解为什么这么分层 | `archive/architecture_refactor_plan.md` | `archive/architecture_refactor_acceptance.md` |
| 打包 exe / 资源路径问题 | `CONVENTIONS.md` §打包 | `QS_infra/resource_path.py` |

> 一次任务最多读 2 份 Tier 1，避免上下文膨胀。归档目录默认不读。

## 五、文档维护规则（写给智能体自己）

- **AGENT_GUIDE.md（本文）≤ 150 行**，超过先精简再写。
- 任何"行数 / 路径 / 函数签名"在 AGENT_GUIDE 中不写，只放在 ARCHITECTURE / INTERFACES——本文档要稳。
- 实现完一次代码改动后，**仅当公共接口变更时**才更新 INTERFACES.md；分层结构改变才更新 ARCHITECTURE.md。
- 不要把会话上下文 / 任务 todo 写进任何 docs/*.md；那是 task list / PR description 的工作。
- 历史决策、已完成的重构计划放进 `docs/archive/`，默认不被加载。
