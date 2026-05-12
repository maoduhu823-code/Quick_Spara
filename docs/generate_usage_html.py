# -*- coding: utf-8 -*-
"""Generate Quick_Sparam feature guide as a self-contained HTML file.

Usage:
    python docs/generate_usage_html.py

Outputs:
    docs/Quick_Sparam_使用指南.html   -- single-file HTML, base64 images embedded
    picture/*.png                     -- source images (UI screenshots + charts)
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
PICTURE_DIR = ROOT / "picture"
OUTPUT_HTML = DOCS_DIR / "Quick_Sparam_使用指南.html"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Annotation specs
# rect = (left%, top%, right%, bottom%) as percentages of image width/height
# ---------------------------------------------------------------------------

SECTIONS = [
    {
        "id": "overview",
        "title": "主界面总览",
        "subtitle": "软件启动后的主界面，五个核心区域覆盖日常操作的全部入口。",
        "screenshot": "main_window",
        "annotations": [
            {"n": 1, "label": "文件操作区",
             "desc": "打开/关闭文件、查看文件信息、保存处理结果",
             "rect": (1.1, 3.4, 13.5, 31.5)},
            {"n": 2, "label": "S参数操作区",
             "desc": "端口降阶/重排/级联/差分转换/频域分析的入口按钮",
             "rect": (1.1, 34.2, 13.5, 68.2)},
            {"n": 3, "label": "文件列表区",
             "desc": "已加载的文件列表；单选或多选决定哪些文件参与绘图或分析",
             "rect": (15.9, 3.4, 70.4, 64.2)},
            {"n": 4, "label": "绘图控制区",
             "desc": "输入端口对、选择参数类型与数据切面，点击绘图按钮",
             "rect": (15.9, 67.9, 70.4, 97.7)},
            {"n": 5, "label": "信息输出区",
             "desc": "实时显示处理日志、端口信息、警告和错误",
             "rect": (71.8, 3.4, 99.4, 98.2)},
        ],
        "steps": [],
        "tip": "",
    },
    {
        "id": "quick-plot",
        "title": "快速绘图：5 步上手",
        "subtitle": "打开文件后，按以下步骤即可在 matplotlib 窗口看到 S 参数曲线。",
        "screenshot": "main_window",
        "annotations": [
            {"n": 1, "label": "打开 .snp 文件",
             "desc": "点击「打开文件」按钮，支持一次多选",
             "rect": (1.7, 6.8, 12.9, 11.3)},
            {"n": 2, "label": "在列表中选中文件",
             "desc": "单击选一个，Ctrl+单击多选，Shift+单击范围选",
             "rect": (16.6, 6.0, 69.7, 62.6)},
            {"n": 3, "label": "输入端口对",
             "desc": "端口输入框，格式：1 3  或  1:5  或  1:2:5",
             "rect": (25.7, 70.4, 42.8, 76.7)},
            {"n": 4, "label": "选参数与切面",
             "desc": "选择 S/Y/Z 参数类型，选幅度(dB)/相位/群延迟等切面",
             "rect": (49.2, 74.5, 69.5, 87.2)},
            {"n": 5, "label": "点击绘图",
             "desc": "点击绘图按钮，matplotlib 窗口弹出曲线",
             "rect": (16.5, 82.9, 43.2, 90.4)},
        ],
        "steps": [
            ("打开 .snp 文件",
             "点击左侧「文件操作区」的「打开文件」按钮，选择一个或多个 Touchstone "
             "格式（.s2p / .s4p 等）文件。"),
            ("在列表中选中目标文件",
             "文件加载后出现在中央文件列表。单击选一个；Ctrl+单击多选；Shift+单击范围选。"),
            ("输入端口对",
             "在「绘图控制区」的端口 1 和端口 2 输入框中填写端口编号。"
             "格式支持：<code>1 3</code>（逐个）、<code>1:5</code>（连续）、"
             "<code>1:2:5</code>（步进）。"),
            ("选择参数类型与数据切面",
             "从下拉菜单选 S/Y/Z，再选幅度(dB)、相位、群延迟、实部、虚部等切面。"),
            ("点击「绘图」",
             "matplotlib 窗口弹出曲线，图例自动显示文件名和端口对。"),
        ],
        "tip": ("端口对格式示例：端口 1 填 <code>1 3</code>、端口 2 填 <code>2 4</code>，"
                "勾选「一一对应」只绘 S<sub>1,2</sub> 和 S<sub>3,4</sub>；"
                "取消勾选则绘制所有组合。"),
        "extra": "curves",
    },
    {
        "id": "port-management",
        "title": "端口管理",
        "subtitle": "绘图或分析之前先修正端口信息，可以避免后续端口误配。",
        "screenshot": "port_management",
        "annotations": [
            {"n": 1, "label": "元数据",
             "desc": "编辑端口名（便于后续按名称选端口），修改参考阻抗（仅更新标注，不重归一化）",
             "rect": (5, 8, 95, 31)},
            {"n": 2, "label": "拓扑变换",
             "desc": "端口重排（拖拽）、端口合并、端口降阶/缩并，操作后生成新的 S 参数对象",
             "rect": (5, 34, 95, 58)},
            {"n": 3, "label": "阻抗变换",
             "desc": "端接指定阻抗、重新归一化参考阻抗，改变 S 矩阵内容",
             "rect": (5, 61, 95, 80)},
        ],
        "steps": [
            ("进入端口管理",
             "在主界面左侧「S参数操作区」点击「端口管理」按钮。"),
            ("（可选）编辑端口名",
             "给每个端口命名（如 TX+、RX- 等），后续操作可按名称填端口，减少输错端口号的风险。"),
            ("（可选）拓扑变换",
             "需要重新排列端口顺序，或合并、缩并端口时，在「拓扑变换」组操作。"),
            ("（可选）阻抗变换",
             "修改参考阻抗或端接特定阻抗（100 Ω 差分转 50 Ω 单端等场景）。"),
            ("保存结果",
             "操作后会生成新的 S 参数对象，建议立即查看「文件信息」或保存为新文件。"),
        ],
        "tip": "推荐操作顺序：端口名 → 端口顺序 → 阻抗/缩并 → 保存结果。改变顺序可能导致后续配对出错。",
    },
    {
        "id": "diff-conversion",
        "title": "差分转换（单端 → 混合模式）",
        "subtitle": "将单端 S 参数转换为差分（SDD/SCC/SCD/SDC）混合模式参数。",
        "screenshot": "diff_conversion",
        "annotations": [
            {"n": 1, "label": "选择端口排布逻辑",
             "desc": "决定差分线的默认配对：按线（每条线的两端口）或按侧（驱动侧/接收侧）",
             "rect": (3, 4, 97, 14)},
            {"n": 2, "label": "确认端口排布图",
             "desc": "图示说明当前配对关系；可进一步指定哪些 line 参与部分差分",
             "rect": (3, 16, 97, 49)},
            {"n": 3, "label": "设置差分阻抗",
             "desc": "差分参考阻抗，通常为 100 Ω；应与实际测试夹具保持一致",
             "rect": (3, 51, 97, 60)},
            {"n": 4, "label": "选择输出模式",
             "desc": "「只输出 SDD」适合快速查看差分通道；完整混合模式保留全部 4 个子矩阵",
             "rect": (3, 76, 97, 86)},
        ],
        "steps": [
            ("选中文件并打开对话框",
             "在主界面选中目标文件，点击「差分转换」。"),
            ("选择端口排布逻辑",
             "按线：每条 diff line 的两个单端口（P1、P2）映射为一对；"
             "按侧：驱动侧全为 P1、接收侧全为 P2。"),
            ("（部分差分）指定参与的 line",
             "勾选「部分差分」后，在输入框填写需要转换的 line 编号，未填写的保持单端。"),
            ("设置差分阻抗并执行",
             "输入差分参考阻抗（默认 100 Ω），点击「确定」生成混合模式 S 参数。"),
        ],
        "tip": ("完整混合模式（SDD + SCD + SDC + SCC）适合诊断共模串扰；"
                "只需要差分通道则选「只输出 SDD」，节省文件大小。"),
    },
    {
        "id": "freq-analysis",
        "title": "频域批量分析",
        "subtitle": "对多文件/多条 line 批量计算插损、回损、串扰、群延迟等指标，可导出 Excel。",
        "screenshot": "freq_analysis",
        "annotations": [
            {"n": 1, "label": "勾选分析项目",
             "desc": "选择要计算的指标：插损、回损、串扰、PN skew、群延迟、VTF……",
             "rect": (3, 5, 97, 23)},
            {"n": 2, "label": "指定端口排布",
             "desc": "配置 line 数量、端口分配和传输方向，影响 line / 串扰计算结果",
             "rect": (3, 25, 97, 59)},
            {"n": 3, "label": "输入关注频点",
             "desc": "输入若干频点（GHz），分析结果将在这些频点处标注具体数值",
             "rect": (3, 61, 97, 78)},
            {"n": 4, "label": "绘图或导出 Excel",
             "desc": "点击「绘图」查看曲线；点击「导出数据为 Excel」生成报告文件",
             "rect": (3, 80, 97, 96)},
        ],
        "steps": [
            ("先在主界面选中目标文件",
             "频域分析对选中的所有文件批量运行，注意先在文件列表选好。"),
            ("点击「频域分析」进入对话框",
             "在主界面「S参数操作区」点击「频域分析」按钮。"),
            ("勾选需要的分析项目",
             "插损（IL）、回损（RL）、串扰（NEXT/FEXT）、PN skew、群延迟（GD）、VTF 均可独立勾选。"),
            ("配置端口排布",
             "填写 line 数量和端口分配方式；若只看「最差通道」可直接勾选「最差 line」模式。"),
            ("输入关注频点并执行",
             "填写若干频点（如 5 10 20 GHz）后点击「绘图」查看曲线，"
             "或「导出数据为 Excel」生成报告。"),
        ],
        "tip": "批量分析前确认端口排布图与实际封装/连接器拓扑一致，否则 line 串扰矩阵位置会错位。",
    },
    {
        "id": "cascade",
        "title": "S 参数级联",
        "subtitle": "通过表格指定相邻网络的连接端口，将多个 .snp 文件串联成一个复合网络。",
        "screenshot": "cascade",
        "annotations": [
            {"n": 1, "label": "快速填端口",
             "desc": "点击「所有端口/按边/按线」将端口号批量填入表格",
             "rect": (2, 5, 98, 18)},
            {"n": 2, "label": "配置文件和连接端口",
             "desc": "每行选一个 .snp 文件；左端口=网络输入侧，右端口=与下一网络相连的端口",
             "rect": (2, 20, 98, 82)},
            {"n": 3, "label": "确认生成",
             "desc": "点击「确定」后生成级联 S 参数，加入主窗口文件列表",
             "rect": (2, 84, 98, 96)},
        ],
        "steps": [
            ("打开级联对话框",
             "在「S参数操作区」点击「S参数级联」按钮。"),
            ("在表格中选择文件顺序",
             "每行对应一个网络；按级联顺序排列，相邻行通过右端口 ↔ 左端口相连。"),
            ("填写连接端口",
             "点击快速填表按钮（所有端口/按边/按线）自动填入，或手动输入端口编号。"),
            ("检查颜色配对",
             "相同颜色的单元格表示连接关系；需保证相邻网络的连接端口数量一致。"),
            ("点击「确定」生成",
             "生成后的复合网络自动加入主窗口文件列表，可直接绘图或保存。"),
        ],
        "tip": "相邻网络的右端口数量必须和下一个网络的左端口数量相同，否则矩阵维度不匹配。",
    },
    {
        "id": "ripple",
        "title": "Ripple 分析",
        "subtitle": "对 S 参数插损曲线进行纹波拟合，量化曲线的波动特性。",
        "screenshot": "ripple",
        "annotations": [
            {"n": 1, "label": "端口对",
             "desc": "输入待分析的端口 1 和端口 2，格式与主界面绘图控制区相同",
             "rect": (3, 6, 97, 35)},
            {"n": 2, "label": "频率范围",
             "desc": "分析的频率上限（GHz）；低于该频点的数据参与拟合",
             "rect": (3, 37, 97, 50)},
            {"n": 3, "label": "拟合方法",
             "desc": "多项式拟合、IEEE 802.3-2022（标准化方法）或 Savitzky-Golay 平滑",
             "rect": (3, 52, 97, 70)},
            {"n": 4, "label": "执行分析",
             "desc": "点击「分析」后弹出拟合曲线和 Ripple 残差图",
             "rect": (3, 80, 97, 95)},
        ],
        "steps": [
            ("选中文件并打开对话框",
             "在主界面选中目标文件，点击「Ripple 分析」按钮。"),
            ("填写端口对",
             "输入端口 1 和端口 2（格式与主界面绘图控制区相同）。"),
            ("设置频率范围和拟合方法",
             "填写截止频点（GHz）；IEEE 802.3-2022 适合 SerDes 链路评估。"),
            ("点击「分析」查看结果",
             "弹出两张图：原始曲线 + 拟合曲线，以及 Ripple 残差图。"),
        ],
        "tip": "IEEE 802.3-2022 方法是以太网标准规定的多项式拟合变体，结果可直接引用到合规性报告中。",
    },
    {
        "id": "time-domain",
        "title": "时域分析（TDR / 冲激 / 阶跃 / 脉冲）",
        "subtitle": "将频域 S 参数逆傅里叶变换到时域，查看 TDR 阻抗、冲激和阶跃响应。",
        "screenshot": "time_domain",
        "annotations": [
            {"n": 1, "label": "波形类型",
             "desc": "TDR（阶跃反射）、Impulse（冲激）、Step（阶跃透射）、Pulse（脉冲）",
             "rect": (2, 3, 98, 12)},
            {"n": 2, "label": "时域参数",
             "desc": "设置上升沿时间、时间步长和采样点数",
             "rect": (2, 14, 60, 36)},
            {"n": 3, "label": "兼容性检查",
             "desc": "自动检测频率步长和最高频率；绿色=正常，黄色=需注意，红色=风险",
             "rect": (62, 14, 98, 36)},
            {"n": 4, "label": "添加端口对",
             "desc": "填写端口号后点击「添加」，支持多条曲线叠加",
             "rect": (2, 38, 98, 74)},
            {"n": 5, "label": "绘图控制",
             "desc": "选择是否叠加多条曲线、是否显示阻抗转换刻度",
             "rect": (2, 76, 98, 90)},
        ],
        "steps": [
            ("打开时域分析对话框",
             "在「S参数操作区」点击「时域分析」按钮（需要已加载文件）。"),
            ("选择波形类型",
             "TDR 适合查看阻抗不连续点；Impulse / Step 适合传输信道特性评估。"),
            ("设置时域参数",
             "上升沿时间越小、频率上限越高分辨率越好，但需要文件有足够带宽。"),
            ("检查兼容性状态",
             "绿色表示参数与文件带宽兼容；黄色警告需评估是否影响结果；红色则建议调整参数。"),
            ("添加端口对并绘图",
             "填写端口 1/端口 2，点击「添加」后列表出现该曲线；点击「绘图」弹出时域波形。"),
        ],
        "tip": "TDR 波形的 Y 轴可以切换为阻抗（Ω）显示，便于直接读取传输线的特征阻抗。",
    },
]


# Sidebar navigation groups: (group_label, [section_id, ...])
NAV_GROUPS = [
    ("界面总览",   ["overview"]),
    ("快速上手",   ["quick-plot"]),
    ("模块详解",   ["port-management", "diff-conversion", "freq-analysis",
                    "cascade", "ripple", "time-domain"]),
    ("工作流",     ["workflow-ddr", "delivery"]),
]

# DDR end-to-end workflow steps
DDR_WORKFLOW_STEPS = [
    {
        "n": 1,
        "title": "S 参数级联",
        "module_id": "cascade",
        "module_label": "→ 模块：S参数级联",
        "status": "available",
        "desc": (
            "将 SoC PKG、PCB Board 和 DRAM PKG 三段 S 参数依次级联，"
            "生成端到端通道模型。级联顺序固定：SoC_pkg.snp → board.snp → dram_pkg.snp。"
            "每段文件的端口顺序应事先确认（驱动侧端口在左，负载侧端口在右）。"
        ),
        "tip": (
            "DDR5/LPDDR5 通常为 50 Ω 单端参考阻抗；确保三段文件参考阻抗一致，"
            "否则级联前需先做阻抗归一化。"
        ),
    },
    {
        "n": 2,
        "title": "部分差分转换",
        "module_id": "diff-conversion",
        "module_label": "→ 模块：差分转换",
        "status": "available",
        "desc": (
            "仅对 DQS 和 WCK 差分时钟线做单端→差分转换，其余 DQ 数据线保持单端。"
            "在对话框中选「部分差分」，在 line 输入框填写 DQS/WCK 对应的 line 编号。"
        ),
        "tip": (
            "DDR DQS 为差分读写选通信号，LPDDR5 WCK 为写时钟；"
            "DQ 为单端数据信号，不需要转换。差分阻抗通常设 100 Ω。"
        ),
    },
    {
        "n": 3,
        "title": "端口阻抗归一化",
        "module_id": "port-management",
        "module_label": "→ 模块：端口管理",
        "status": "available",
        "desc": (
            "根据 SoC 驱动阻抗 Ron 和 DRAM 片上终端 ODT 修正参考阻抗，"
            "使 S 参数反映实际电路工作点。在「端口管理 → 阻抗变换」中设置驱动端和接收端端口的参考阻抗。"
        ),
        "tip": (
            "DDR5 典型值：Ron ≈ 34 Ω，ODT ≈ 40~48 Ω；"
            "LPDDR5X 可能更低（Ron ≈ 20~30 Ω）。需查阅 PHY Databook 和 DRAM 规格书。"
        ),
    },
    {
        "n": 4,
        "title": "频域批量分析",
        "module_id": "freq-analysis",
        "module_label": "→ 模块：频域分析",
        "status": "available",
        "desc": (
            "对端到端通道做频域分析：重点关注串扰和（NEXT + FEXT 之和）、"
            "VTF（电压传输函数，即 SDD21）以及插损在 DDR5/LPDDR5X 奈奎斯特频率处的数值。"
            "勾选「最差 line」模式可快速定位问题通道。"
        ),
        "tip": (
            "DDR5-6400 奈奎斯特 = 3.2 GHz；"
            "LPDDR5X-8533 奈奎斯特 ≈ 4.27 GHz；"
            "LPDDR5X-9600 奈奎斯特 ≈ 4.8 GHz。"
        ),
    },
    {
        "n": 5,
        "title": "时域波形及 SNR 分析",
        "module_id": "time-domain",
        "module_label": "→ 模块：时域分析",
        "status": "coming-soon",
        "desc": (
            "将 S 参数转换到时域，观察脉冲响应，叠加串扰后评估 ISI + 串扰对 SNR 的影响。"
            "<br><em style='color:#9eaabb'>该功能正在开发中，预计支持：脉冲响应叠加、"
            "SNR 自动计算、眼图前分析（Eye Diagram pre-cursor analysis）。</em>"
        ),
        "tip": (
            "当前可使用「时域分析」模块查看 TDR / 冲激 / 阶跃响应作为初步参考；"
            "完整 SNR 分析模块上线后将直接集成到此工作流。"
        ),
    },
]


# ---------------------------------------------------------------------------
# Matplotlib chart generation
# ---------------------------------------------------------------------------

def generate_charts() -> dict[str, Path]:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    COLORS = ["#177e89", "#e59f2e", "#da3e43", "#4e6d8c", "#6b3fa0"]
    paths: dict[str, Path] = {}

    sample_files = [
        (ROOT / "samples" / "StackupDemo1_test.s4p", "Demo-1"),
        (ROOT / "samples" / "Twinax line-Spara1G.s4p", "Twinax"),
        (ROOT / "samples" / "connector_model.s4p", "Connector"),
    ]

    import skrf
    networks: list[tuple] = []
    for fpath, name in sample_files:
        if fpath.exists():
            try:
                nw = skrf.Network(str(fpath))
                networks.append((nw, name))
            except Exception as exc:
                print(f"  [警告] 加载失败 {fpath.name}: {exc}")

    if not networks:
        print("  [警告] 未找到示例文件，跳过曲线图生成")
        return paths

    # Chart 1: S21 insertion loss + S11 return loss side by side
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for i, (nw, name) in enumerate(networks):
        c = COLORS[i % len(COLORS)]
        fghz = nw.f / 1e9
        if nw.nports >= 2:
            s21 = 20 * np.log10(np.abs(nw.s[:, 1, 0]) + 1e-300)
            axes[0].plot(fghz, s21, color=c, lw=1.6, label=name)
        s11 = 20 * np.log10(np.abs(nw.s[:, 0, 0]) + 1e-300)
        axes[1].plot(fghz, s11, color=c, lw=1.6, label=name)

    for ax, title, ylabel in [
        (axes[0], "S21 插损 (dB)", "幅度 (dB)"),
        (axes[1], "S11 回损 (dB)", "幅度 (dB)"),
    ]:
        ax.set_xlabel("频率 (GHz)", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.22, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=1.5)
    out = PICTURE_DIR / "s_param_comparison.png"
    fig.savefig(str(out), dpi=130, bbox_inches="tight")
    plt.close(fig)
    paths["s_param_comparison"] = out
    print(f"  曲线图: {out.name}")

    # Chart 2: Full S-matrix for first network
    nw0, name0 = networks[0]
    n = min(nw0.nports, 4)
    fig2, ax2 = plt.subplots(figsize=(11, 4.5))
    for m in range(n):
        for k in range(n):
            sdb = 20 * np.log10(np.abs(nw0.s[:, m, k]) + 1e-300)
            ax2.plot(nw0.f / 1e9, sdb, lw=1.2, alpha=0.85,
                     color=COLORS[(m * n + k) % len(COLORS)],
                     label=f"S{m+1}{k+1}")
    ax2.set_xlabel("频率 (GHz)", fontsize=11)
    ax2.set_ylabel("幅度 (dB)", fontsize=11)
    ax2.set_title(f"{name0} -- 全矩阵 S 参数", fontsize=12, fontweight="bold")
    ax2.legend(ncol=4, fontsize=9, loc="lower left")
    ax2.grid(True, alpha=0.22, linestyle="--")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    fig2.tight_layout(pad=1.5)
    out2 = PICTURE_DIR / "s_param_full_matrix.png"
    fig2.savefig(str(out2), dpi=130, bbox_inches="tight")
    plt.close(fig2)
    paths["s_param_full_matrix"] = out2
    print(f"  曲线图: {out2.name}")

    return paths


# ---------------------------------------------------------------------------
# Qt UI screenshot capture
# ---------------------------------------------------------------------------

def capture_screenshots() -> dict[str, Path]:
    from PyQt6.QtWidgets import QApplication, QListWidgetItem
    from PyQt6.QtGui import QFont

    from main_window import SParameterViewer_MainWin
    from QS_dialogs.cascade import CascadeDialog
    from QS_dialogs.freq_analysis import frequencyAnalysisDialog
    from QS_dialogs.port_management import PortManagementDialog
    from QS_dialogs.ripple import RippleFitDialog
    from QS_dialogs.se2diff import DiffConversionDialog
    from QS_dialogs.time_domain import TimeDomainDialog

    os.environ.pop("QT_QPA_PLATFORM", None)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 9))

    def pump(n: int = 10) -> None:
        for _ in range(n):
            app.processEvents()

    original_stdout = sys.stdout
    paths: dict[str, Path] = {}

    def grab(widget, name: str, size: tuple | None = None) -> None:
        if size:
            widget.resize(*size)
        widget.show()
        pump(12)
        pixmap = widget.grab()
        out = PICTURE_DIR / f"{name}.png"
        if not pixmap.save(str(out)):
            raise RuntimeError(f"截图保存失败: {out}")
        widget.close()
        pump(4)
        sys.stdout = original_stdout
        paths[name] = out
        print(f"  截图: {name}.png")

    sample_files = [
        ROOT / "samples" / "StackupDemo1_test.s4p",
        ROOT / "samples" / "Twinax line-Spara1G.s4p",
        ROOT / "samples" / "connector_model.s4p",
    ]

    # Main window with demo state
    main = SParameterViewer_MainWin()
    sys.stdout = original_stdout
    for f in sample_files:
        main.file_list.addItem(str(f))
    for i in range(main.file_list.count()):
        main.file_list.item(i).setSelected(i < 2)
    main.port1_input.setText("1 3")
    main.port2_input.setText("2 4")
    main.param_type_combo.setCurrentText("S参数")
    main.facet_combo.setCurrentText("幅度(dB)")
    main.mapping_combo.setCurrentText("一 一对应")
    main.freG_input.setText("10")
    main.same_plot_checkbox.setChecked(True)
    main.output_console.setPlainText(
        "演示流程:\n"
        "1. 打开一个或多个 .snp 文件\n"
        "2. 输入端口对并选择数据切面\n"
        "3. 点击绘图或进入分析/转换模块\n"
        "4. 在信息输出区查看处理日志"
    )
    grab(main, "main_window", (1500, 700))

    grab(PortManagementDialog(None), "port_management", (420, 300))

    diff = DiffConversionDialog(4, None)
    diff.partial_diff_radio.setChecked(True)
    diff.diff_lines_edit.setText("1 2")
    grab(diff, "diff_conversion")

    freq = frequencyAnalysisDialog({}, None)
    freq.analysis_checks["insertion_loss"].setChecked(True)
    freq.analysis_checks["return_loss"].setChecked(True)
    freq.analysis_checks["group_delay"].setChecked(True)
    freq.line_input.setText("1:4")
    freq.freG_input.setText("1 5 10 20")
    grab(freq, "freq_analysis", (950, 520))

    cascade = CascadeDialog(None, ["connector_model.s4p", "board_model.s4p"])
    if cascade.table.rowCount() >= 2:
        cascade.table.item(0, 1).setText("1 2")
        cascade.table.item(0, 2).setText("3 4")
        cascade.table.item(1, 1).setText("3 4")
        cascade.table.item(1, 2).setText("1 2")
        cascade.set_pair_colors()
    grab(cascade, "cascade", (1200, 500))

    ripple = RippleFitDialog(None, [str(sample_files[0])])
    ripple.port1_input.setText("1")
    ripple.port2_input.setText("2")
    ripple.stop_freq_input.setText("20")
    ripple.fit_method.setCurrentText("IEEE_std_802.3-2022")
    grab(ripple, "ripple", (620, 330))

    td = TimeDomainDialog({}, None)
    td._port1_edit.setText("1")
    td._port2_edit.setText("1")
    td._port_list.addItem(QListWidgetItem("StackupDemo1_test.s4p  S1,1  [TDR]"))
    grab(td, "time_domain", (900, 680))

    sys.stdout = original_stdout
    return paths


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def img_tag(path: Path, cls: str = "", style: str = "") -> str:
    data = b64(path)
    cls_attr = f' class="{cls}"' if cls else ""
    style_attr = f' style="{style}"' if style else ""
    return f'<img src="data:image/png;base64,{data}"{cls_attr}{style_attr} alt="{path.stem}">'


def ann_pins_html(anns: list[dict]) -> str:
    """Position numbered badges at each annotation point (no obscuring boxes)."""
    parts = []
    for a in anns:
        if "point" in a:
            px, py = a["point"]
        else:
            l, t, r, b = a["rect"]
            px, py = (l + r) / 2, (t + b) / 2
        parts.append(
            f'<div class="ann-pin" style="left:{px:.1f}%;top:{py:.1f}%">'
            f'<span class="badge">{a["n"]}</span></div>'
        )
    return "\n".join(parts)


def legend_html(anns: list[dict]) -> str:
    items = ""
    for a in anns:
        items += (
            f'<div class="legend-item">'
            f'<span class="badge-inline">{a["n"]}</span>'
            f'<div><strong>{a["label"]}</strong>'
            f'<span class="desc"> &mdash; {a["desc"]}</span></div>'
            f'</div>\n'
        )
    return f'<div class="legend">{items}</div>'


def steps_html(steps: list[tuple]) -> str:
    if not steps:
        return ""
    items = ""
    for i, (title, body) in enumerate(steps, 1):
        items += (
            f'<div class="step-item">'
            f'<span class="step-num">{i}</span>'
            f'<div class="step-body"><strong>{title}</strong>'
            f'<p>{body}</p></div>'
            f'</div>\n'
        )
    return f'<div class="steps">{items}</div>'


def tip_html(tip: str) -> str:
    if not tip:
        return ""
    return f'<div class="tip-box"><strong>提示：</strong>{tip}</div>'


def workflow_html() -> str:
    steps = [
        ("①", "导入文件", "打开一个或多个 .snp"),
        ("②", "确认端口", "端口名、顺序、阻抗"),
        ("③", "快速绘图", "输入端口对与数据切面"),
        ("④", "分析转换", "频域、时域、级联、差分"),
        ("⑤", "保存导出", "保存 S 参数或 Excel"),
    ]
    cards = ""
    for i, (num, title, body) in enumerate(steps):
        arrow = '<span class="wf-arrow">›</span>' if i < len(steps) - 1 else ""
        cards += (
            f'<div class="wf-card">'
            f'<div class="wf-num">{num}</div>'
            f'<div class="wf-title">{title}</div>'
            f'<div class="wf-body">{body}</div>'
            f'</div>{arrow}'
        )
    return f'<div class="workflow">{cards}</div>'


def render_ddr_workflow_html() -> str:
    context = (
        '<div class="wf-context">'
        "<strong>应用场景：</strong>DDR5 / LPDDR5X 信号完整性分析，"
        "从三段 S 参数到时域 SNR 评估<br>"
        "<strong>涉及模块：</strong>S参数级联 → 差分转换（部分） → "
        "端口管理（阻抗归一化） → 频域分析 → 时域分析<br>"
        "<strong>典型输入件：</strong>"
        "SoC_pkg.snp &nbsp;+&nbsp; PCB_board.snp &nbsp;+&nbsp; DRAM_pkg.snp"
        "</div>"
    )

    steps_html_str = ""
    for s in DDR_WORKFLOW_STEPS:
        status_label = "可用" if s["status"] == "available" else "开发中"
        steps_html_str += (
            f'<div class="wf-step">'
            f'  <div class="wf-step-circle {s["status"]}">{s["n"]}</div>'
            f'  <div class="wf-step-body">'
            f'    <div class="wf-step-head">'
            f'      <h3>{s["title"]}</h3>'
            f'      <span class="status-tag {s["status"]}">{status_label}</span>'
            f'      <a class="module-ref" href="#{s["module_id"]}">'
            f'        {s["module_label"]}</a>'
            f'    </div>'
            f'    <div class="wf-step-desc">{s["desc"]}</div>'
            f'    <div class="wf-step-tip">{s["tip"]}</div>'
            f'  </div>'
            f'</div>\n'
        )

    return (
        f'\n<section class="section" id="workflow-ddr">\n'
        f'  <div class="section-header">\n'
        f'    <h2>工作流：DDR 端到端串扰与信道分析</h2>\n'
        f'    <div class="subtitle">'
        f'DDR5 / LPDDR5X 通道从封装+PCB+封装 S 参数到时域 SNR 的完整分析流程。</div>\n'
        f'  </div>\n'
        f'  {context}\n'
        f'  <div class="wf-timeline">{steps_html_str}</div>\n'
        f'</section>\n'
    )


# ---------------------------------------------------------------------------
# CSS + JS
# ---------------------------------------------------------------------------

CSS = (
    "*{box-sizing:border-box;margin:0;padding:0}"
    "body{font-family:'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',sans-serif;"
    "background:#f4f6f9;color:#2d343d;line-height:1.65}"
    "a{color:#177e89;text-decoration:none}"
    "code{background:#e8f3f4;padding:1px 5px;border-radius:3px;font-size:.88em;"
    "font-family:Consolas,monospace;color:#177e89}"
    ".layout{display:flex;min-height:100vh}"
    ".sidebar{width:230px;min-width:230px;background:#1c2734;color:#b0bec5;"
    "position:sticky;top:0;height:100vh;overflow-y:auto;flex-shrink:0}"
    ".sidebar-inner{padding:20px 0 40px}"
    ".sidebar h1{font-size:13px;font-weight:700;padding:0 18px 14px;color:#ecf0f4;"
    "border-bottom:1px solid #2a3a4a;margin-bottom:10px;letter-spacing:.5px}"
    ".sidebar a{display:block;padding:6px 18px;font-size:12.5px;color:#8fa0b0;"
    "transition:background .15s,color .15s}"
    ".sidebar a:hover,.sidebar a.active{color:#fff;background:rgba(255,255,255,.06);"
    "border-left:3px solid #177e89;padding-left:15px}"
    ".sb-group-title{display:block;padding:12px 18px 4px;font-size:10.5px;"
    "font-weight:700;color:#4e6070;text-transform:uppercase;letter-spacing:.8px}"
    ".main{flex:1;padding:36px 48px 60px;max-width:1060px}"
    ".page-header{margin-bottom:32px;padding-bottom:20px;border-bottom:1px solid #dce4eb}"
    ".page-header h1{font-size:28px;color:#1c2734;font-weight:700}"
    ".page-header .tagline{font-size:14px;color:#627080;margin-top:6px}"
    ".page-header .meta{font-size:12px;color:#9eaabb;margin-top:8px}"
    ".workflow{display:flex;align-items:center;gap:0;margin:20px 0 8px;flex-wrap:wrap}"
    ".wf-card{background:#fff;border:1px solid #d0dde6;border-radius:8px;"
    "padding:14px 18px;min-width:130px;text-align:center;flex:1}"
    ".wf-num{font-size:20px;color:#177e89;font-weight:700;margin-bottom:4px}"
    ".wf-title{font-size:14px;font-weight:600;color:#1c2734}"
    ".wf-body{font-size:12px;color:#627080;margin-top:4px}"
    ".wf-arrow{font-size:22px;color:#b0bec5;padding:0 6px;flex-shrink:0}"
    ".section{background:#fff;border-radius:10px;box-shadow:0 1px 5px rgba(0,0,0,.07);"
    "padding:28px 32px;margin-bottom:32px}"
    ".section-header{margin-bottom:14px}"
    ".section-header h2{font-size:19px;color:#1c2734;border-left:4px solid #177e89;"
    "padding-left:12px;line-height:1.3}"
    ".section-header .subtitle{font-size:13px;color:#627080;margin-top:6px;padding-left:16px}"
    ".screenshot-wrap{position:relative;display:block;border:1px solid #cdd8e3;"
    "border-radius:6px;overflow:hidden;margin:16px 0 10px;line-height:0}"
    ".screenshot-wrap img{width:100%;display:block}"
    ".ann-pin{position:absolute;pointer-events:none;"
    "transform:translate(-50%,-50%)}"
    ".badge{display:inline-flex;align-items:center;justify-content:center;"
    "width:24px;height:24px;border-radius:50%;background:#da3e43;color:#fff;"
    "font-size:12px;font-weight:700;"
    "box-shadow:0 2px 6px rgba(0,0,0,.45);border:2px solid rgba(255,255,255,.85)}"
    ".legend{display:flex;flex-wrap:wrap;gap:8px 24px;margin:10px 0 16px;"
    "padding:14px 16px;background:#f8fafc;border-radius:6px;"
    "border:1px solid #e4eaef}"
    ".legend-item{display:flex;align-items:flex-start;gap:8px;font-size:13px;min-width:260px}"
    ".badge-inline{display:inline-flex;align-items:center;justify-content:center;"
    "width:20px;height:20px;min-width:20px;border-radius:50%;"
    "background:#da3e43;color:#fff;font-size:11px;font-weight:700;"
    "flex-shrink:0;margin-top:1px}"
    ".legend-item strong{color:#1c2734}"
    ".legend-item .desc{color:#627080}"
    ".steps{margin-top:16px}"
    ".step-item{display:flex;gap:14px;margin-bottom:13px;align-items:flex-start}"
    ".step-num{display:flex;align-items:center;justify-content:center;"
    "width:26px;height:26px;min-width:26px;border-radius:50%;"
    "background:#177e89;color:#fff;font-size:12px;font-weight:700;margin-top:2px}"
    ".step-body strong{font-size:14px;color:#1c2734}"
    ".step-body p{font-size:13px;color:#4a5562;margin-top:3px;line-height:1.6}"
    ".tip-box{background:#e6f4f5;border-left:4px solid #177e89;border-radius:4px;"
    "padding:10px 14px;margin:14px 0;font-size:13px;color:#2d343d}"
    ".tip-box strong{color:#177e89}"
    ".chart-img{width:100%;border:1px solid #cdd8e3;border-radius:6px;margin:6px 0 4px}"
    ".chart-caption{font-size:12px;color:#9eaabb;text-align:center;margin-bottom:10px}"
    ".del-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}"
    ".del-card{background:#f8fafc;border:1px solid #e0e8ef;border-radius:8px;padding:16px}"
    ".del-card h3{font-size:14px;color:#177e89;margin-bottom:8px}"
    ".del-card ul{list-style:disc;padding-left:18px;font-size:13px;color:#4a5562;line-height:1.8}"
    ".footer{margin-top:48px;padding-top:16px;border-top:1px solid #dce4eb;"
    "font-size:12px;color:#9eaabb}"
    ".wf-timeline{margin-top:20px}"
    ".wf-step{display:flex;gap:20px;margin-bottom:0;position:relative}"
    ".wf-step:not(:last-child)::before{content:'';position:absolute;left:19px;top:42px;"
    "width:2px;height:calc(100% - 10px);background:#d0dde6;z-index:0}"
    ".wf-step-circle{width:40px;height:40px;min-width:40px;border-radius:50%;"
    "display:flex;align-items:center;justify-content:center;"
    "font-size:16px;font-weight:700;color:#fff;flex-shrink:0;z-index:1;"
    "box-shadow:0 2px 6px rgba(0,0,0,.18)}"
    ".wf-step-circle.available{background:#177e89}"
    ".wf-step-circle.coming-soon{background:#9eaabb}"
    ".wf-step-body{flex:1;padding:0 0 28px}"
    ".wf-step-head{display:flex;align-items:center;gap:10px;margin-bottom:6px}"
    ".wf-step-head h3{font-size:15px;font-weight:700;color:#1c2734}"
    ".status-tag{font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600}"
    ".status-tag.available{background:#d4f0ec;color:#177e89}"
    ".status-tag.coming-soon{background:#f0f2f4;color:#9eaabb}"
    ".module-ref{font-size:11px;color:#177e89;padding:2px 8px;"
    "border:1px solid #b8e0e4;border-radius:10px;margin-left:auto;white-space:nowrap}"
    ".wf-step-desc{font-size:13px;color:#4a5562;line-height:1.7}"
    ".wf-step-tip{background:#f8fafc;border-left:3px solid #d0dde6;border-radius:3px;"
    "padding:7px 12px;margin-top:8px;font-size:12px;color:#627080}"
    ".wf-context{background:#1c2734;border-radius:8px;padding:14px 18px;margin:16px 0;"
    "color:#b0bec5;font-size:13px;line-height:1.7}"
    ".wf-context strong{color:#ecf0f4}"
)

JS = (
    "document.addEventListener('DOMContentLoaded',function(){"
    "var links=document.querySelectorAll('.sidebar a');"
    "var obs=new IntersectionObserver(function(entries){"
    "entries.forEach(function(e){"
    "if(e.isIntersecting){"
    "links.forEach(function(l){l.classList.remove('active')});"
    "var a=document.querySelector('.sidebar a[href=\"#'+e.target.id+'\"]');"
    "if(a)a.classList.add('active');}});},"
    "{rootMargin:'-30% 0px -60% 0px'});"
    "document.querySelectorAll('section[id]').forEach(function(s){obs.observe(s)});"
    "});"
)


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _nav_link_title(sid: str) -> str:
    if sid == "delivery":
        return "交付与复核"
    for sec in SECTIONS:
        if sec["id"] == sid:
            return sec["title"]
    if sid == "workflow-ddr":
        return "DDR 端到端分析"
    return sid


def build_html(screenshots: dict[str, Path], charts: dict[str, Path]) -> str:
    nav_links = ""
    for group_label, ids in NAV_GROUPS:
        nav_links += f'<span class="sb-group-title">{group_label}</span>\n'
        for sid in ids:
            nav_links += f'<a href="#{sid}">{_nav_link_title(sid)}</a>\n'

    section_html = ""
    for sec in SECTIONS:
        shot_key = sec.get("screenshot")
        shot_path = screenshots.get(shot_key) if shot_key else None

        screenshot_block = ""
        legend_block = ""
        if shot_path and shot_path.exists():
            screenshot_block = (
                '<div class="screenshot-wrap">'
                + img_tag(shot_path)
                + ann_pins_html(sec["annotations"])
                + "</div>"
            )
            legend_block = legend_html(sec["annotations"])

        extra_block = ""
        if sec.get("extra") == "curves":
            parts = []
            for key, caption in [
                ("s_param_comparison",
                 "图示：插损 S21（左）与回损 S11（右）对比，示例使用 samples/ 中的样本文件"),
                ("s_param_full_matrix",
                 "图示：全矩阵 S 参数（S11 ~ S44），可在主界面「绘图控制区」直接生成"),
            ]:
                p = charts.get(key)
                if p and p.exists():
                    parts.append(
                        img_tag(p, cls="chart-img")
                        + f'<div class="chart-caption">{caption}</div>'
                    )
            if parts:
                extra_block = (
                    '<div style="margin-top:20px">'
                    '<h3 style="font-size:15px;color:#1c2734;margin-bottom:10px">'
                    "实际绘图效果示例</h3>"
                    + "".join(parts)
                    + "</div>"
                )

        section_html += (
            f'\n<section class="section" id="{sec["id"]}">\n'
            f'  <div class="section-header">\n'
            f'    <h2>{sec["title"]}</h2>\n'
            f'    <div class="subtitle">{sec["subtitle"]}</div>\n'
            f"  </div>\n"
            f"  {screenshot_block}\n"
            f"  {legend_block}\n"
            f"  {steps_html(sec['steps'])}\n"
            f"  {tip_html(sec.get('tip', ''))}\n"
            f"  {extra_block}\n"
            f"</section>\n"
        )

    delivery = (
        '\n<section class="section" id="delivery">\n'
        '  <div class="section-header">\n'
        "    <h2>交付与复核建议</h2>\n"
        '    <div class="subtitle">让结果可复现、可追溯、可复查。</div>\n'
        "  </div>\n"
        '  <div class="del-grid">\n'
        '    <div class="del-card"><h3>文件归档</h3><ul>\n'
        "      <li>原始 .snp 与处理后 .snp 一同归档</li>\n"
        "      <li>文件名保留能说明处理动作的后缀<br>"
        "（如 _se2diff、_cascade_2stage）</li>\n"
        "      <li>Excel 结果放报告正文，.snp 单独存档</li>\n"
        "    </ul></div>\n"
        '    <div class="del-card"><h3>结果复核</h3><ul>\n'
        "      <li>用「文件信息」核查端口数和阻抗</li>\n"
        "      <li>信息输出区保留关键处理日志截图</li>\n"
        "      <li>批量分析前确认端口排布图与实际拓扑一致</li>\n"
        "    </ul></div>\n"
        "  </div>\n"
        "</section>\n"
    )

    today = date.today().strftime("%Y-%m-%d")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Quick_Sparam 使用指南</title>\n"
        f"<style>{CSS}</style>\n"
        f"<script>{JS}</script>\n"
        "</head>\n<body>\n"
        '<div class="layout">\n'
        '  <nav class="sidebar"><div class="sidebar-inner">\n'
        "    <h1>Quick_Sparam</h1>\n"
        f"    {nav_links}"
        "  </div></nav>\n"
        '  <main class="main">\n'
        '    <div class="page-header">\n'
        "      <h1>Quick_Sparam 使用指南</h1>\n"
        '      <div class="tagline">面向 RF S 参数文件的查看、端口处理、级联、差分转换、频域/时域分析和结果导出</div>\n'
        f'      <div class="meta">封装SIPI开发部 &nbsp;&middot;&nbsp; 生成日期：{today} &nbsp;&middot;&nbsp; 适用格式：.snp（.s2p / .s4p / …）</div>\n'
        "    </div>\n"
        '\n    <section class="section" id="workflow" style="margin-bottom:24px">\n'
        '      <div class="section-header">\n'
        "        <h2>典型操作流程</h2>\n"
        '        <div class="subtitle">从原始 Touchstone 文件到曲线、转换结果和 Excel 报告。</div>\n'
        "      </div>\n"
        f"      {workflow_html()}\n"
        '      <div class="tip-box" style="margin-top:14px"><strong>注意：</strong>'
        "端口相关操作会生成新的网络对象，建议操作后立即查看「文件信息」或保存。"
        "批量分析前先选中目标文件，并确认端口排布方式与实际拓扑一致。</div>\n"
        "    </section>\n"
        f"{section_html}"
        f"{render_ddr_workflow_html()}"
        f"{delivery}"
        '    <div class="footer">自动生成脚本：<code>docs/generate_usage_html.py</code>'
        " &nbsp;&middot;&nbsp; 截图：PyQt6 widget.grab() &nbsp;&middot;&nbsp; 曲线图：matplotlib Agg</div>\n"
        "  </main>\n</div>\n</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    PICTURE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    print("[ 1/3 ] 生成 matplotlib 曲线图 ...")
    charts = generate_charts()

    print("[ 2/3 ] 截取 UI 界面截图 ...")
    screenshots = capture_screenshots()

    print("[ 3/3 ] 构建 HTML ...")
    html = build_html(screenshots, charts)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\n完成！\n  HTML : {OUTPUT_HTML}\n  图片 : {PICTURE_DIR}")


if __name__ == "__main__":
    main()
