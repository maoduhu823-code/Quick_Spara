"""
信息收集功能的极简配置入口。

只复用用户资料、使用记录和评价反馈功能时，优先修改本文件和 path_config.py。
本文件不依赖试用授权和版本更新模块，可以随信息收集代码单独分享。
"""

from __future__ import annotations


# ===== 应用基础信息 =====
APP_NAME = "Quick_Sparam"
APP_VERSION = "2026.03"


# ===== 用户资料问卷配置 =====
PROFILE_SCHEMA_VERSION = 1
# "missing_only": 本地资料缺失时才弹问卷；"every_start": 每次启动都弹出预填问卷。
PROFILE_PROMPT_MODE = "missing_only"
REQUIRED_PROFILE_FIELDS = ("department", "lm_group", "pl_group", "project_name")

USAGE_SURVEY_WINDOW_TITLE = "用户信息登记"
USAGE_SURVEY_INTRO = "首次使用前请补充以下信息，用于内部试用统计和需求跟踪。"
USER_NAME_PLACEHOLDER = "非必填"
DEPARTMENT_OTHER_PLACEHOLDER = "请输入部门"
LM_GROUP_OTHER_PLACEHOLDER = "请输入LM大组"
PL_GROUP_OTHER_PLACEHOLDER = "请输入PL小组"
PROJECT_FIELD_LABEL = "应用于哪些项目:"
PROJECT_PLACEHOLDER = "交付、技术项目均可，多个项目可用逗号分隔"

# ===== 用户资料问卷选项 =====
OTHER_OPTION = "其他"
PRIMARY_DEPARTMENT = "封装SIPI开发部"
DEPARTMENT_OPTIONS = [PRIMARY_DEPARTMENT, OTHER_OPTION]
LM_GROUP_OPTIONS = ["电性能技术", "泛终端", "泛无线", "网络计算", "硬件", OTHER_OPTION]
LM_GROUP_OPTIONS_FOR_OTHER_DEPARTMENT = [OTHER_OPTION]
PL_GROUP_OPTIONS_BY_LM = {
    "电性能技术": ["图灵PI", "存储技术组", OTHER_OPTION],
    "泛终端": ["无线终端", "短距离", "终端芯片", OTHER_OPTION],
    "泛无线": ["无线数字", "网络射频", "无线射频", OTHER_OPTION],
    "网络计算": ["图灵SI组", "IPNP", "光联接", OTHER_OPTION],
    "硬件": [
        "平台EVB硬件一组", "平台EVB硬件二组", "泛无线硬件", "网络计算硬件",
        "互连仿真工艺", OTHER_OPTION,
    ],
}
PL_GROUP_OPTIONS_FOR_OTHER_LM = [OTHER_OPTION]

USER_DATA_HEADERS = [
    "填写时间", "主机名", "用户姓名", "部门", "LM大组", "PL小组", "应用项目名",
    "App版本",
]
USAGE_HEADERS = ["主机名", "启动时间", "关闭时间"]


# ===== 评价&反馈问卷配置 =====
FEEDBACK_WINDOW_TITLE = "评价&反馈"
FEEDBACK_INTRO = "欢迎补充软件使用评价和后续需求，便于内部版本规划和优先级判断。"
USAGE_INTENSITY_TITLE = "使用强度"
POINT_EFFICIENCY_TITLE = "单点效率提高程度"
OVERALL_EFFICIENCY_TITLE = "整体效率提高程度"
REQUEST_GROUP_TITLE = "需求反馈"
OVERALL_SCORE_TITLE = "整体评分"
POINT_EFFICIENCY_HELP = "针对某个单点工作&流程，例如：串扰和计算、级联S参数、做竞品频域性能分析"
OVERALL_EFFICIENCY_HELP = "针对满足项目过点所需的某个大类工作流程：TR* 后仿S参数优化效果统计输出"
POINT_EFFICIENCY_NOTE_PLACEHOLDER = "可补充具体工作流、对比方式或估算依据，非必填"
OVERALL_EFFICIENCY_NOTE_PLACEHOLDER = "可补充项目级收益、节省环节或协作收益，非必填"
REQUEST_TEXT_PLACEHOLDER = "请描述具体场景、当前痛点、期望结果；如果是bug，请尽量写复现步骤"

USAGE_INTENSITY_OPTIONS = [
    "<1h/周", "1-2h/周", "2-3h/周", "3-5h/周", ">5h/周",
]
EFFICIENCY_OPTIONS = [
    "<25%", "25%-50%", "50%-75%", "75%-100%", ">100%",
]
REQUEST_IMPORTANCE_OPTIONS = ["低", "中", "高", "非常高"]
REQUEST_URGENCY_OPTIONS = ["不急", "一般", "较急", "非常紧急"]
REQUEST_DIMENSION_OPTIONS = [
    "UI交互", "Bug反馈", "工作流增加", "单点功能增加", "功能改进",
    "性能/稳定性", "结果可信度", "文档/示例", "其他",
]
DEFAULT_REQUEST_IMPORTANCE = "中"
DEFAULT_REQUEST_URGENCY = "一般"
DEFAULT_REQUEST_DIMENSION = "Bug反馈"

FEEDBACK_HEADERS = [
    "提交时间", "用户姓名", "主机名", "部门", "LM大组", "PL小组", "应用项目名",
    "整体评分", "使用强度", "单点效率提高程度", "单点效率补充", "整体效率提高程度",
    "整体效率补充", "需求重要度", "需求紧急度", "需求维度", "需求描述",
    "附件", "App版本",
]
EMPTY_COMBO_TEXT = "未选择"
