# -*- coding: utf-8 -*-
"""
统计图表页（Mock）
==================
分类占比环形图 + 月度趋势柱状图。顶部增加月份选择器，
切换月份时：总支出、分类环形图、月度趋势高亮柱全部同步刷新。

数据全部使用前端写死的 Mock 数据，图表背景透明，
颜色统一使用主色调蓝色 #4A7BE8 及其浅色梯度。

# TODO: 接入后端接口（接口契约 v1）
#   GET /api/v1/stats/summary?start&end
#   GET /api/v1/stats/categories?start&end
#   GET /api/v1/stats/trend?start&end&granularity=month
#   分别用返回的 total_amount / count、items、points 替换下方 Mock 数据。
#   切换月份时把 YYYY-MM 转为当月 start/end 再请求。
"""

import plotly.graph_objects as go
import streamlit as st

from services import api_client
from utils import month_range, shift_month_key, to_error_message

# 当前演示月份（前端 Mock 固定为 2026 年 11 月）
CURRENT_MONTH = "2026-11"

# 下拉框：value 用于查询 / 接口参数，label 给用户看。
# TODO: 接口契约 v1 未提供月份列表接口，当前按演示月份固定生成；
#       后续如需真实可选月份，可由前端按当前月生成或与后端补充约定。
#       默认值应取后端返回的“当前月”，这里为了演示写死 2026-11。
MONTH_OPTIONS = [
    ("2026-11", "本月 · 2026年11月"),
    ("2026-10", "上个月 · 2026年10月"),
    ("2026-09", "2026年9月"),
    ("2026-08", "2026年8月"),
    ("2026-07", "2026年7月"),
    ("2026-06", "2026年6月"),
]
MONTH_LABELS = dict(MONTH_OPTIONS)

# ══════════════════════════════════════════════════════════════════
# Mock 数据（按月份组织，切换下拉框时直接查字典）
# 每套数据的 categories 金额合计必须等于当月的 MOCK_MONTHLY_TREND，
# 避免“总支出”和柱状图对不上。
# TODO: 接入后端接口
#   GET /api/v1/stats/categories?start&end（分类占比）
#   GET /api/v1/stats/trend?start&end&granularity=month（近 6 个月趋势）
#   删除本段 Mock，分别用接口返回的 items / points 渲染。
# ══════════════════════════════════════════════════════════════════
MOCK_STATS = {
    "2026-11": {
        "records": 24,
        "categories": [
            ("餐饮", 500),
            ("购物", 300),
            ("娱乐", 260),
            ("交通", 150),
            ("居住", 90),
            ("其他", 452),
        ],
    },
    "2026-10": {
        "records": 21,
        "categories": [
            ("餐饮", 560),
            ("购物", 420),
            ("娱乐", 180),
            ("交通", 160),
            ("居住", 90),
            ("其他", 270),
        ],
    },
    "2026-09": {
        "records": 19,
        "categories": [
            ("餐饮", 480),
            ("购物", 350),
            ("娱乐", 210),
            ("交通", 130),
            ("居住", 90),
            ("其他", 190),
        ],
    },
    "2026-08": {
        "records": 14,
        "categories": [
            ("餐饮", 380),
            ("购物", 190),
            ("娱乐", 120),
            ("交通", 110),
            ("居住", 90),
            ("其他", 90),
        ],
    },
    "2026-07": {
        "records": 17,
        "categories": [
            ("餐饮", 420),
            ("购物", 250),
            ("娱乐", 160),
            ("交通", 140),
            ("居住", 90),
            ("其他", 100),
        ],
    },
    "2026-06": {
        "records": 12,
        "categories": [
            ("餐饮", 300),
            ("购物", 150),
            ("娱乐", 110),
            ("交通", 100),
            ("居住", 90),
            ("其他", 70),
        ],
    },
}

# 近 6 个月的月度趋势（柱状图数据源）。
# 多准备几个月，保证切到 2026-06 时也能向前展示 1-6 月。
MOCK_MONTHLY_TREND = {
    "2026-01": 1120,
    "2026-02": 1980,
    "2026-03": 1540,
    "2026-04": 760,
    "2026-05": 1320,
    "2026-06": 820,
    "2026-07": 1160,
    "2026-08": 980,
    "2026-09": 1450,
    "2026-10": 1680,
    "2026-11": 1752,
}

BLUE = "#4A7BE8"
BLUE_MUTED = "#D9E4F8"
PIE_COLORS = ["#4A7BE8", "#6D93EE", "#8FAEF2", "#AFC7F6", "#CADBF8", "#E4EDFC"]

_CSS = """
<style>
/* 统计模式没有底部输入框，缩短主区域底部留白 */
[data-testid="stMainBlockContainer"]:has(.stats-title) {
  padding-bottom: 2.5rem !important;
}
.stats-title {
  font-size: 1.4rem; font-weight: 700; color: #111827; letter-spacing: -.01em;
}
.stats-sub { color: #8A93A6; font-size: .85rem; margin: .2rem 0 0 0; }

/* 顶部月份筛选器：浅色描边，和整体极简风一致 */
[data-testid="stMainBlockContainer"]:has(.stats-title) [data-testid="stSelectbox"] {
  margin: 0;
}
[data-testid="stMainBlockContainer"]:has(.stats-title) [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #FFFFFF; border-radius: 10px; border-color: #E5E9F0;
  min-height: 38px; font-size: .84rem;
}
[data-testid="stMainBlockContainer"]:has(.stats-title) [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover {
  border-color: #C9D7F3;
}

/* 总支出摘要；月份切换时这行金额会一起刷新 */
.stats-total-row {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1rem; flex-wrap: wrap; margin: 1.15rem 0 1.05rem 0;
}
.stats-total-label { font-size: .78rem; color: #8A93A6; margin-bottom: .2rem; }
.stats-total-value {
  font-size: 2rem; line-height: 1.1; font-weight: 700; color: #111827;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.stats-total-side {
  display: flex; align-items: center; gap: .45rem; padding-bottom: .3rem;
}
.stats-total-badge {
  font-size: .74rem; color: #5B6B85; background: #EEF4FF;
  border-radius: 999px; padding: .2rem .55rem;
}
.stats-total-delta { font-size: .74rem; color: #8A93A6; }

.stats-chart-title {
  font-size: .92rem; font-weight: 600; color: #374151; margin: .2rem 0 .2rem 0;
}
.stats-chart-hint {
  font-weight: 400; color: #A0A7B4; font-size: .74rem; margin-left: .3rem;
}
</style>
"""

_FONT = dict(
    family='"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
    color="#6B7280",
    size=12,
)
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=_FONT,
    margin=dict(l=10, r=10, t=10, b=10),
)


def _pie_chart(categories, total: float, month: str) -> None:
    """分类占比环形图；中心用 annotation 展示当前选中月份的总支出。"""
    if not categories:
        st.info("当前月份暂无分类数据。")
        return
    labels = [item[0] for item in categories]
    values = [item[1] for item in categories]
    # 分类数超过调色板长度时循环取色，避免接后端后被分类数量卡住。
    slice_colors = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(values))]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=slice_colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="percent",
            textfont=dict(color="#FFFFFF", size=11),
            hovertemplate="%{label}<br>¥%{value:,.0f}<extra></extra>",
            sort=False,
        )
    )
    fig.update_layout(
        **_LAYOUT,
        height=330,
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.18,
            xanchor="center", x=0.5, font=dict(size=11, color="#6B7280"),
        ),
    )

    # 环形图中心留空，用 Plotly annotation 显示总支出。
    # 这是图表内的“中心 Markdown”，比在图表旁边叠加 HTML 更稳。
    fig.add_annotation(
        text=f"<b>¥{total:,.0f}</b>",
        x=0.5, y=0.52,
        showarrow=False,
        font=dict(size=20, color="#111827"),
    )
    fig.add_annotation(
        text="总支出",
        x=0.5, y=0.44,
        showarrow=False,
        font=dict(size=10, color="#8A93A6"),
    )

    # TODO: 接入后端接口 GET /api/v1/stats/categories?start&end -> items
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _bar_chart(selected_month: str, monthly_trend=None) -> None:
    """近 6 个月趋势柱状图；选中月份的柱子用主色高亮。"""
    trend = dict(MOCK_MONTHLY_TREND if monthly_trend is None else monthly_trend)
    all_months = sorted(trend)
    if not all_months:
        st.info("当前月份暂无趋势数据。")
        return
    end = all_months.index(selected_month) if selected_month in all_months else len(all_months) - 1
    window = all_months[max(0, end - 5): end + 1]

    labels = [f"{int(month.split('-')[1])} 月" for month in window]
    amounts = [trend[month] for month in window]
    hover_labels = [f"{month[:4]} 年 {int(month.split('-')[1])} 月" for month in window]

    # 选中月份的柱子用主色，其余月份用低饱和浅蓝。
    colors = [BLUE if month == selected_month else BLUE_MUTED for month in window]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=amounts,
            customdata=hover_labels,
            marker=dict(color=colors, cornerradius=8),
            text=[f"¥{value:,.0f}" for value in amounts],
            textposition="outside",
            textfont=dict(color="#6B7280", size=10),
            hovertemplate="%{customdata}<br>¥%{y:,.0f}<extra></extra>",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        **_LAYOUT,
        height=330,
        showlegend=False,
        yaxis=dict(
            showgrid=True,
            gridcolor="#EEF1F6",
            zeroline=False,
            tickprefix="¥",
            tickfont=dict(size=11, color="#9CA3AF"),
            automargin=True,
        ),
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#9CA3AF")),
        bargap=0.45,
    )

    # 高亮柱只改变颜色，不改变数值；鼠标悬浮可看到完整年月。
    # TODO: 接入后端接口 GET /api/v1/stats/trend?start&end&granularity=month -> points
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _load_real_stats(selected_month: str) -> dict:
    """真实模式：summary + categories + trend 三接口组合成图表数据。"""
    start_date, end_date = month_range(selected_month)
    start, end = start_date.isoformat(), end_date.isoformat()
    summary = api_client.fetch_stats_summary(selected_month) or {}
    category_data = api_client.fetch_stats_category(start, end) or {}

    trend_start = month_range(shift_month_key(selected_month, -5))[0].isoformat()
    trend_data = api_client.fetch_stats_trend(trend_start, end, "month") or {}

    categories = []
    for item in category_data.get("items") or []:
        try:
            categories.append((item.get("category") or "其他",
                               float(item.get("amount") or 0)))
        except (TypeError, ValueError):
            continue

    monthly = {}
    for point in trend_data.get("points") or []:
        key = str(point.get("period") or "")[:7]
        if len(key) == 7:
            try:
                monthly[key] = float(point.get("amount") or 0)
            except (TypeError, ValueError):
                monthly[key] = 0.0

    total = float(summary.get("total_amount")
                  or category_data.get("total_amount") or 0)
    if selected_month not in monthly:
        monthly[selected_month] = total

    return {
        "records": int(summary.get("count") or 0),
        "categories": categories,
        "total": total,
        "monthly": monthly,
    }


def render() -> None:
    """统计模式主区域。"""
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── 月份状态：首次进入默认本月；切换时 Streamlit 自动 rerun ──
    # 注意：st.selectbox 的 widget state 在离开统计页后可能被 Streamlit
    # 清理，所以额外用非 widget 的 _stats_month 记住最近一次选择。
    month_keys = [key for key, _ in MONTH_OPTIONS]
    persisted_month = st.session_state.get("_stats_month", CURRENT_MONTH)
    if persisted_month not in month_keys:
        persisted_month = CURRENT_MONTH
    if st.session_state.get("stats_month") not in month_keys:
        st.session_state["stats_month"] = persisted_month

    selected_month = st.session_state["stats_month"]
    is_current = selected_month == CURRENT_MONTH
    month_num = int(selected_month.split("-")[1])
    is_demo = bool(st.session_state.get("demo_mode", True))
    real_error = None

    if is_demo:
        month_data = MOCK_STATS[selected_month]
        records = month_data["records"]
        categories = month_data["categories"]
        total = sum(amount for _, amount in categories)
        monthly = dict(MOCK_MONTHLY_TREND)
    else:
        try:
            data = _load_real_stats(selected_month)
            records = data["records"]
            categories = data["categories"]
            total = data["total"]
            monthly = data["monthly"]
        except Exception as exc:
            real_error = to_error_message(exc)
            records, categories, total, monthly = 0, [], 0.0, {}

    # 计算环比，让“较上月”也跟随月份变化。
    trend_months = sorted(monthly)
    if selected_month in trend_months:
        trend_index = trend_months.index(selected_month)
    else:
        trend_index = 0
    if trend_index > 0:
        prev_total = monthly[trend_months[trend_index - 1]]
        delta_pct = (total - prev_total) / prev_total * 100 if prev_total else 0
        delta_text = f"较上月 {'+' if delta_pct >= 0 else '-'}{abs(delta_pct):.1f}%"
    else:
        delta_text = "暂无环比数据"

    # ── 顶部标题 + 月份选择器（同一行，右侧对齐）──
    title = "📊 本月消费洞察" if is_current else f"📊 {month_num} 月消费洞察"
    head_left, head_right = st.columns([2.1, 1.0], vertical_alignment="center")
    with head_left:
        st.markdown(f'<div class="stats-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="stats-sub">{selected_month[:4]} 年 {month_num} 月 · '
            f'共 {records} 笔记录 · {"Mock 数据" if is_demo else "接口数据"}</div>',
            unsafe_allow_html=True,
        )
    with head_right:
        st.selectbox(
            "查看月份",
            options=month_keys,
            format_func=lambda key: MONTH_LABELS[key],
            key="stats_month",
            label_visibility="collapsed",
        )
    st.session_state["_stats_month"] = selected_month

    if real_error:
        st.error(f"⚠️ {real_error}")
        return

    # ── 总支出摘要：金额、笔数、环比全部跟月份联动 ──
    total_label = "本月总支出" if is_current else f"{month_num} 月总支出"
    st.markdown(
        '<div class="stats-total-row">'
        '<div>'
        f'<div class="stats-total-label">{total_label}</div>'
        f'<div class="stats-total-value">¥{total:,.2f}</div>'
        '</div>'
        '<div class="stats-total-side">'
        f'<span class="stats-total-badge">共 {records} 笔</span>'
        f'<span class="stats-total-delta">{delta_text}</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── 双图：分类占比 / 近 6 个月趋势 ──
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f'<div class="stats-chart-title">消费分类占比'
            f'<span class="stats-chart-hint">共 {len(categories)} 类</span></div>',
            unsafe_allow_html=True,
        )
        _pie_chart(categories, total, selected_month)
    with right:
        st.markdown(
            '<div class="stats-chart-title">月度消费趋势'
            '<span class="stats-chart-hint">近 6 个月</span></div>',
            unsafe_allow_html=True,
        )
        _bar_chart(selected_month, monthly)
