# HTML 使用指南生成技能 / Skill

> 本文档记录了为 Quick_Sparam 生成图文并茂 HTML 使用指南的完整思路、约定和可复用模板。
> 可直接作为提示词骨架，应用到其他 PyQt6 工具的使用指南生成。

---

## 一、给 Claude 的引导词（复制到新项目对话开头）

```
我希望为 [工具名称] 生成一份图文并茂的中文使用指南（HTML 单文件）。

工具描述：[一句话描述工具功能]
技术栈：PyQt6 桌面应用，Python，matplotlib 可视化
入口文件：[main_script.py]
示例数据目录：[input_test/ 或类似路径]

请先阅读以下文件，然后按 HTML_GUIDE_SKILL.md 的标准实现生成脚本：
- CLAUDE.md（项目结构说明）
- main_window.py（主窗口类）
- dialogs/（各功能对话框）

目标：生成 docs/generate_usage_html.py，运行后输出：
1. docs/[工具名]_使用指南.html（单文件，base64 内嵌图片）
2. picture/*.png（UI 截图 + matplotlib 曲线图）
```

---

## 二、关键设计决策（及理由）

| 决策 | 选择 | 理由 |
|------|------|------|
| 文档格式 | **HTML 单文件** | 浏览器打开，无需 Office；侧边栏导航；CSS 标注不烧录进图片 |
| 图片嵌入 | base64 内嵌 | 单文件可直接分发；picture/ 目录同时保留源图 |
| UI 截图 | PyQt6 `widget.grab()` | 离屏渲染，无需显示器；`processEvents()` 确保渲染完整 |
| 曲线图 | matplotlib Agg 后端 | 无 GUI 依赖；`matplotlib.use("Agg")` 必须在所有其他 import 之前 |
| 标注方式 | **CSS 定位数字圆圈（无边框方框）** | 不遮挡 UI；修改标注文字无需重截图；白边圆圈在任何背景上都清晰 |
| 标注坐标 | `rect=(l%,t%,r%,b%)`，显示时取中心 | 百分比坐标随图片尺寸自动缩放；以矩形记录方便未来加回边框 |

---

## 三、SECTIONS 数据结构模板

```python
SECTIONS = [
    {
        "id": "section-id",           # HTML 锚点，侧边栏 href
        "title": "章节标题",
        "subtitle": "一句话说明这一节讲什么。",
        "screenshot": "screenshot_key", # 对应 capture_screenshots() 返回的 key
        "annotations": [
            {
                "n": 1,               # 数字编号（显示在红色圆圈内）
                "label": "区域名称",   # 图例里的短标题
                "desc": "详细说明，显示在图例里",
                "rect": (l, t, r, b), # 区域范围，百分比，0-100
                # "point": (x, y),    # 可选：手动指定徽章位置（百分比）
                                      # 默认取 rect 中心
            },
        ],
        "steps": [                    # 步骤列表（空列表则不显示）
            ("步骤标题", "步骤说明文字，支持 <code>内联代码</code> 和 HTML。"),
        ],
        "tip": "提示文字（可留空）",   # 显示为蓝色提示框
        # "extra": "curves",          # 可选，值为 "curves" 时在本节末尾插入曲线图
    },
]
```

### 目录分组结构（NAV_GROUPS）

```python
NAV_GROUPS = [
    ("界面总览",  ["overview"]),
    ("快速上手",  ["quick-plot"]),
    ("模块详解",  ["module-a", "module-b", ...]),
    ("工作流",    ["workflow-xxx", "delivery"]),
]
```

---

## 四、工作流 section 结构模板

工作流区别于单模块介绍——它是跨模块的步骤序列，用时间轴卡片展示。

```python
MY_WORKFLOW_STEPS = [
    {
        "n": 1,
        "title": "步骤标题",
        "module_id": "对应模块的 section id",   # 点击跳转
        "module_label": "→ 模块：XXX",
        "status": "available",                   # 或 "coming-soon"
        "desc": "步骤详细说明（支持 HTML）",
        "tip": "注意事项或典型参数值",
    },
    # ... 更多步骤
]
```

---

## 五、截图注意事项

```python
# 截图前必做：
original_stdout = sys.stdout
main = SParameterViewer_MainWin()
sys.stdout = original_stdout   # 主窗口会重定向 stdout，截图后要恢复

# 截图时：
widget.show()
for _ in range(12):            # 多轮 pump 确保 Qt 完成渲染
    app.processEvents()
pixmap = widget.grab()

# 每次 grab 后恢复 stdout（防止对话框也重定向）
sys.stdout = original_stdout
```

---

## 六、matplotlib 曲线图注意事项

```python
# 最顶部（在所有 import 之前）：
import matplotlib
matplotlib.use("Agg")          # 必须在 pyplot、skrf、Qt 之前

# 图表风格建议：
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(True, alpha=0.22, linestyle="--")
```

---

## 七、常见 SIPI 工作流场景（可直接扩展到工作流章节）

以下场景来自封装 SIPI 工程师实际需求，可按需加入使用指南的「工作流」章节：

### 1. DDR5 / LPDDR5X 端到端串扰分析
**流程：** 级联（SoC_pkg + PCB + DRAM_pkg） → 部分差分转换（DQS/WCK） → 端口阻抗归一化（Ron/ODT） → 频域分析（串扰和、VTF） → 时域波形  
**关键指标：** 奈奎斯特频率处插损、NEXT+FEXT 串扰和、群延迟偏差  
**DDR5-6400 奈奎斯特 = 3.2 GHz；LPDDR5X-8533 ≈ 4.27 GHz**

### 2. PCIe Gen5/Gen6 差分通道合规性
**流程：** SE2diff → 检查 SDD11/SDD21 @ 16 GHz（PCIe 5.0 奈奎斯特） → Ripple 拟合（IEEE 802.3）去除封装谐振毛刺 → 频域批量分析  
**关键指标：** SDD11 < -10 dB，SDD21 > -3 dB，共模抑制 > 25 dB

### 3. USB4 / Thunderbolt 多通道阻抗匹配
**流程：** 端口重命名（TX1+/−, RX1+/− …） → 端口重排 → SE2diff → 频域分析（每通道 RL/IL） → TDR 定位阻抗不连续点  
**关键指标：** 差分阻抗 85±10 Ω，通道间偏斜 < 10 ps

### 4. RDIMM 时钟 / 地址 / 数据线表征
**流程：** 加载多端口 .snp → 端口重排（按 CLK/ADDR/DATA 分组） → TDR 定位封装引线寄生 → Ripple 拟合（SG 平滑）→ 批量导出 Excel  
**关键指标：** CLK IL < -1.5 dB @ 2.4 GHz，DATA-DATA NEXT < -15 dB

### 5. Via / 过孔存根效应隔离
**流程：** 加载含过孔通道 + 单独过孔模型 → 级联（去嵌入方向反转） → 端口降阶 → 比较 IL/RL before/after  
**关键指标：** 过孔谐振频率，IL 差异（dB）

### 6. 差分→共模转换诊断（Mode Conversion）
**流程：** SE2diff → 提取 SDC/SCD 子矩阵 → 频域分析（SDD vs SCC vs SDC）  
**关键指标：** SDC < -25 dB（低模式转换），SDD/SCC 分离 > 10 dB

### 7. 多连接器 PCB 通道端到端验证
**流程：** 加载 TX 连接器 + PCB 走线 + RX 连接器 → 三段级联 → 端口重排（对齐通道号） → 频域批量分析 → 导出 Excel（按 JESD82/PCIe 规格打标）  
**关键指标：** 端到端 IL 平坦度 < 1 dB，RL > -18 dB，通道间偏斜 < 5 ps

---

## 八、更新与维护约定

| 触发条件 | 动作 |
|----------|------|
| 新增对话框或功能按钮 | 在 `SECTIONS` 加新 entry；在 `capture_screenshots()` 加 `grab()` 调用 |
| 界面布局改变 | 重新估算 `annotations[*]["rect"]` 坐标；重新运行脚本截图 |
| 新工作流场景 | 在 `DDR_WORKFLOW_STEPS`（或新建 `XXX_WORKFLOW_STEPS`）加 entry |
| 重新生成 | `python docs/generate_usage_html.py`（约 30–60 秒） |

生成脚本本身会在 HTML footer 标注生成日期和脚本路径，方便溯源。

---

## 九、已知限制

- **matplotlib 图表不能直接从 Qt 控件截图**：图表在独立 matplotlib 窗口中，无法通过 `widget.grab()` 获取。当前方案是用 `skrf` 直接绘图并 `savefig()`，保存到 `picture/`。
- **对话框截图无实际数据**：`widget.grab()` 只能抓取渲染状态，若对话框需要真实数据驱动（如频域分析结果图），需要先加载 Network 对象触发计算再截图。
- **Windows 平台特定**：`widget.grab()` 在无头 Linux CI 上可能失败，需配合 virtual framebuffer (Xvfb)。
