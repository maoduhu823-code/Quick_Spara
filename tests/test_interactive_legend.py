"""attach_interactive_legend 的最小验收测试。

Agg 后端避免拉起 Qt（产品代码禁用 matplotlib.use，但测试环境允许）。
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pytest
from matplotlib.backend_bases import PickEvent, MouseEvent, KeyEvent

from app_utils import attach_interactive_legend, attach_legend_toolbar_button


@pytest.fixture
def fig_with_lines():
    fig, ax = plt.subplots()
    l1, = ax.plot([0, 1, 2], [0, 1, 0], label='alpha')
    l2, = ax.plot([0, 1, 2], [1, 0, 1], label='beta')
    yield fig, ax, [l1, l2]
    plt.close(fig)


def _pick(fig, artist, *, shift=False):
    me = MouseEvent('button_press_event', fig.canvas, 0, 0, button=1,
                    key='shift' if shift else None)
    fig.canvas.callbacks.process(
        'pick_event',
        PickEvent('pick_event', fig.canvas, mouseevent=me, artist=artist),
    )


def _key(fig, key):
    fig.canvas.callbacks.process(
        'key_press_event', KeyEvent('key_press_event', fig.canvas, key, 0, 0),
    )


def test_attach_returns_legend_with_two_entries(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    assert legend is not None
    assert len(legend.get_lines()) == 2
    assert {t.get_text() for t in legend.get_texts()} == {'alpha', 'beta'}


def test_legend_is_draggable_when_requested(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    assert legend.get_draggable() is True


def test_both_marker_and_text_are_pickable(fig_with_lines):
    """关键：legend 文字也要响应 pick，否则单击文字不联动高亮。"""
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    for artist in list(legend.get_lines()) + list(legend.get_texts()):
        assert artist.get_picker() is not None


def test_disabled_features_skip_setup(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(
        ax, lines=lines,
        draggable=False, toggle_on_pick=False, context_menu=False,
    )
    assert legend.get_draggable() is False
    for artist in list(legend.get_lines()) + list(legend.get_texts()):
        assert artist.get_picker() is None


def test_no_lines_returns_none():
    fig, ax = plt.subplots()
    try:
        assert attach_interactive_legend(ax) is None
    finally:
        plt.close(fig)


def test_pick_on_marker_invokes_highlight_callback(fig_with_lines):
    fig, ax, lines = fig_with_lines
    picked = []
    legend = attach_interactive_legend(ax, lines=lines, on_legend_pick=picked.append)
    _pick(fig, legend.get_lines()[0])
    assert picked == [lines[0]]
    assert lines[0].get_visible() is True


def test_pick_on_text_invokes_highlight_callback(fig_with_lines):
    """legend 文字单击也应该联动高亮——这正是用户反馈的回归。"""
    fig, ax, lines = fig_with_lines
    picked = []
    legend = attach_interactive_legend(ax, lines=lines, on_legend_pick=picked.append)
    _pick(fig, legend.get_texts()[1])
    assert picked == [lines[1]]


def test_shift_pick_toggles_visibility_even_with_callback(fig_with_lines):
    fig, ax, lines = fig_with_lines
    picked = []
    legend = attach_interactive_legend(ax, lines=lines, on_legend_pick=picked.append)
    _pick(fig, legend.get_lines()[0], shift=True)
    assert picked == []
    assert lines[0].get_visible() is False
    _pick(fig, legend.get_lines()[0], shift=True)
    assert lines[0].get_visible() is True


def test_plain_pick_falls_back_to_toggle_when_no_callback(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    _pick(fig, legend.get_lines()[0])
    assert lines[0].get_visible() is False


def test_toggle_key_default_is_ctrl_l(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    assert legend.get_visible() is True
    _key(fig, 'l')
    assert legend.get_visible() is True       # 单按 l 避开 matplotlib 默认 yscale
    _key(fig, 'ctrl+l')
    assert legend.get_visible() is False
    _key(fig, 'ctrl+l')
    assert legend.get_visible() is True


def test_toggle_key_custom_value(fig_with_lines):
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines, toggle_key='h')
    _key(fig, 'h')
    assert legend.get_visible() is False


def test_toolbar_button_silent_when_no_toolbar(fig_with_lines):
    """Agg 后端无 NavigationToolbar；helper 应返回 None 而不是报错。"""
    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    assert attach_legend_toolbar_button(fig, legend, lines) is None


def test_legend_rename_map_pairs_text_with_origin(fig_with_lines):
    """批量改名对话框依赖这条 mapping —— 验证它列出所有条目。"""
    from app_utils import _legend_rename_map

    fig, ax, lines = fig_with_lines
    legend = attach_interactive_legend(ax, lines=lines)
    pairs = _legend_rename_map(legend, lines)
    assert len(pairs) == 2
    text_set = {t.get_text() for t, _ in pairs}
    line_set = {ln for _, ln in pairs}
    assert text_set == {'alpha', 'beta'}
    assert line_set == set(lines)
