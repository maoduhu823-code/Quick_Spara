"""
生成 resources/ 目录下的 6 张端口示意图 PNG。
运行：python docs/generate_port_diagrams.py
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

# ── 字号配置（按需修改这里）──────────────────────────────
FONT_PORT_LABEL = 11    # Port_1 / Port_n/2 等端口标签
FONT_SNP        = 18    # 中央 "SnP" 粗体
FONT_TITLE      = 14    # 顶部标题（正向传输 / 反向传输）
FONT_SUBTITLE   = 11    # 底部副标题（按线排布 / 按侧排布）
# ─────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')

# ── 端口标签定义 ─────────────────────────────────────────
INLINE_LEFT  = ['Port_1',   'Port_3',   r'$\vdots$', 'Port_n-3', 'Port_n-1']
INLINE_RIGHT = ['Port_2',   'Port_4',   r'$\vdots$', 'Port_n-2', 'Port_n'  ]
INSIDE_LEFT  = ['Port_1',   'Port_2',   r'$\vdots$', 'Port_n/2-1', 'Port_n/2'  ]
INSIDE_RIGHT = ['Port_n/2+1', 'Port_n/2+2', r'$\vdots$', 'Port_n-1', 'Port_n']


def _draw_box(ax):
    """画中央 SnP 方框并返回 (box_left, box_right, box_bottom, box_top)。"""
    bl, br, bb, bt = 3.2, 6.8, 1.5, 8.5
    fancy = mpatches.FancyBboxPatch(
        (bl, bb), br - bl, bt - bb,
        boxstyle='round,pad=0.15',
        facecolor='#d0e8f8', edgecolor='#4a8ab0', linewidth=1.8,
    )
    ax.add_patch(fancy)
    return bl, br, bb, bt


def _draw_ports(ax, labels_left, labels_right, bl, br, bb, bt):
    """在方框两侧画端口线和标签。"""
    n = len(labels_left)
    ys = [bb + (bt - bb) * (i + 0.5) / n for i in range(n - 1, -1, -1)]

    for y, label in zip(ys, labels_left):
        is_dots = label == r'$\vdots$'
        if is_dots:
            ax.text(bl - 0.15, y, label, ha='right', va='center',
                    fontsize=FONT_PORT_LABEL + 2)
        else:
            ax.plot([bl, bl - 1.1], [y, y], 'k-', lw=1.2)
            ax.plot(bl - 1.1, y, 'ko', markersize=4)
            ax.text(bl - 1.3, y, label, ha='right', va='center',
                    fontsize=FONT_PORT_LABEL)

    for y, label in zip(ys, labels_right):
        is_dots = label == r'$\vdots$'
        if is_dots:
            ax.text(br + 0.15, y, label, ha='left', va='center',
                    fontsize=FONT_PORT_LABEL + 2)
        else:
            ax.plot([br, br + 1.1], [y, y], 'k-', lw=1.2)
            ax.plot(br + 1.1, y, 'ko', markersize=4)
            ax.text(br + 1.3, y, label, ha='left', va='center',
                    fontsize=FONT_PORT_LABEL)


def _draw_snp(ax):
    ax.text(5, 5, 'SnP', ha='center', va='center',
            fontsize=FONT_SNP, fontweight='bold', color='#1a5f8a')


def _draw_arrow(ax, direction):
    """direction: 'forward'（红色右箭头）或 'reverse'（蓝色左箭头）。"""
    if direction == 'forward':
        ax.annotate('', xy=(5.9, 5), xytext=(4.1, 5),
                    arrowprops=dict(arrowstyle='->', color='#cc0000',
                                   lw=3.5, mutation_scale=30))
    else:
        ax.annotate('', xy=(4.1, 5), xytext=(5.9, 5),
                    arrowprops=dict(arrowstyle='->', color='#336699',
                                   lw=3.5, mutation_scale=30))


def make_fig():
    fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=100)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect('equal')
    ax.axis('off')
    return fig, ax


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, bbox_inches='tight', dpi=100)
    plt.close(fig)
    print(f'已保存: {path}')


# ── 1. Port_inline.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INLINE_LEFT, INLINE_RIGHT, bl, br, bb, bt)
_draw_snp(ax)
save(fig, 'Port_inline.PNG')

# ── 2. Port_inside.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INSIDE_LEFT, INSIDE_RIGHT, bl, br, bb, bt)
_draw_snp(ax)
save(fig, 'Port_inside.PNG')

# ── 3. inline_posi.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INLINE_LEFT, INLINE_RIGHT, bl, br, bb, bt)
_draw_arrow(ax, 'forward')
ax.text(5, 9.3, '正向传输', ha='center', va='center',
        fontsize=FONT_TITLE, fontweight='bold', color='#cc0000')
ax.text(5, 0.6, '按线排布', ha='center', va='center',
        fontsize=FONT_SUBTITLE, color='#444444')
save(fig, 'inline_posi.PNG')

# ── 4. inline_nega.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INLINE_LEFT, INLINE_RIGHT, bl, br, bb, bt)
_draw_arrow(ax, 'reverse')
ax.text(5, 9.3, '反向传输', ha='center', va='center',
        fontsize=FONT_TITLE, fontweight='bold', color='#336699')
ax.text(5, 0.6, '按线排布', ha='center', va='center',
        fontsize=FONT_SUBTITLE, color='#444444')
save(fig, 'inline_nega.PNG')

# ── 5. inside_posi.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INSIDE_LEFT, INSIDE_RIGHT, bl, br, bb, bt)
_draw_arrow(ax, 'forward')
ax.text(5, 9.3, '正向传输', ha='center', va='center',
        fontsize=FONT_TITLE, fontweight='bold', color='#cc0000')
ax.text(5, 0.6, '按侧排布', ha='center', va='center',
        fontsize=FONT_SUBTITLE, color='#444444')
save(fig, 'inside_posi.PNG')

# ── 6. inside_nega.PNG ───────────────────────────────────
fig, ax = make_fig()
bl, br, bb, bt = _draw_box(ax)
_draw_ports(ax, INSIDE_LEFT, INSIDE_RIGHT, bl, br, bb, bt)
_draw_arrow(ax, 'reverse')
ax.text(5, 9.3, '反向传输', ha='center', va='center',
        fontsize=FONT_TITLE, fontweight='bold', color='#336699')
ax.text(5, 0.6, '按侧排布', ha='center', va='center',
        fontsize=FONT_SUBTITLE, color='#444444')
save(fig, 'inside_nega.PNG')
