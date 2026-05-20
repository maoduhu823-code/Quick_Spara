# CLAUDE.md

> Quick_Sparam 的 AI 协作上下文统一维护在 [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md)。
> 请优先阅读该文件，按其中"任务路由"按需拉取 `docs/ARCHITECTURE.md` / `INTERFACES.md` / `CONVENTIONS.md`。
> 历史重构计划与验收报告已归档至 `docs/archive/`，默认不读。

## 硬约束（必读，正文细节见 AGENT_GUIDE.md §三 与 CONVENTIONS.md）

- `QS_domain/` 与 `QS_services/` 内禁止 `import PyQt6`
- 禁止在模块级调用 `matplotlib.use(...)`（同环境 PyQt5 + PyQt6 会冲突，需让 matplotlib 自动选 `QtAgg`）
- 所有 UI 字符串使用简体中文；字体配置统一走 `app_utils.configure_matplotlib()`
- 新算法放入 `QS_domain/algorithms/`，`sparam_core.py` 仅作向后兼容 shim
- 提交前必须跑 `python -m pytest tests/ -q`
- `QS_runtime_services/` 是独立子系统（试用/版本/反馈），未经授权不要改动

## 运行 / 打包

```bash
# 测试版（源码 + PyCharm）
python Quick_Sparam_B.py             # 空白启动，完整功能
python Quick_Sparam_B.py --dev       # 预填一组本机调试文件 + 端口

# 安装版
pyinstaller Quick_Sparam_install.spec  # runtime hook 注入 QS_LIMITED=1 → 自动隐藏 S 参数操作区的"时域分析"对话框入口
```
