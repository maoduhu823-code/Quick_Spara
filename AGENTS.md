# AGENTS.md

> Quick_Sparam 的 AI 协作上下文统一维护在 [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md)。
> 本文件（供 Codex 等智能体加载）只保留最小硬约束，正文一律到 AGENT_GUIDE.md 查阅。
> 与 `CLAUDE.md` 内容相同；之所以保留两份指针，是因为不同智能体默认加载的文件名不同。

## 硬约束

- `QS_domain/` 与 `QS_services/` 内禁止 `import PyQt6`
- 禁止在模块级调用 `matplotlib.use(...)`
- UI 字符串简体中文；字体配置走 `app_utils.configure_matplotlib()`
- 新算法放进 `QS_domain/algorithms/`；`sparam_core.py` 仅作向后兼容 shim
- 提交前 `python -m pytest tests/ -q`
- `QS_runtime_services/` 不要改

## 运行

```bash
python Quick_Sparam_B.py        # 生产入口
python QSB_test.py              # 本地调试入口（不打包）
```
