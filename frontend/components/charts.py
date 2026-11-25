# -*- coding: utf-8 -*-
"""
图表组件（数据全部来自 api 层统计接口，前端不自行计算金额）：
  - render_category_pie()：消费分类占比环形图（GET /api/stats/category）
  - render_monthly_bar()：月度消费趋势柱状图（GET /api/stats/monthly）
图表配色遵循全局设计规范：蓝 + 灰，克制不花哨；隐藏 Plotly 工具栏，
仅保留 hover 提示，无复杂动画。
"""

import plotly.graph_objects as go
import streamlit as st

from utils import cents_to_yuan

# 蓝灰渐变调色板（主色蓝 + 中性灰，整体不超过 3 个色系）
_PALETTE = ["#4A7BE8", "#7FA3EE", "#A8C2F2", "#C9D9F6", "#DDE8FA",
            "#98A2B3", "#C0C7D2", "#8E97A8", "#B9C4D8"]

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="PingFang SC, Microsoft YaHei, Segoe UI, sans-serif",
              size=13, color="#5B6472"),
    margin=dict(l=10, r=10, t=20, b=10),
)


def render_category_pie(data):
    """消费分类占比环形图（donut）。

    data（GET /api/stats/category 出参）：
      {"total_cents": N, "items": [{"category_name", "amount_cents", "ratio"}, ...]}
    返回 True=已渲染；False=暂无数据（调用方显示「暂无数据」占位文案）。
    """
    items = (data or {}).get("items") or []
    if not items:
        return False
    labels = [i.get("category_name", "未分类") for i in items]
    values = [cents_to_yuan(i.get("amount_cents") or 0) for i in items]
    total_yuan = cents_to_yuan((data or {}).get("total_cents") or 0)

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55, sort=False,
        marker=dict(colors=_PALETTE[:len(labels)], line=dict(color="#FFFFFF", width=2)),
        textinfo="percent", textfont=dict(size=12),
        hovertemplate="%{label}<br>¥%{value:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        height=340,
        showlegend=True,
        legend=dict(orientation="h", x=0.5, y=-0.12, xanchor="center"),
        annotations=[dict(
            text=f"总支出<br><b>¥{total_yuan:,.2f}</b>",
            x=0.5, y=0.5, showarrow=False, align="center",
            font=dict(size=13, color="#5B6472"),
        )],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    return True


def render_monthly_bar(data):
    """月度消费趋势柱状图。

    data（GET /api/stats/monthly 出参）：
      {"items": [{"month": "YYYY-MM", "amount_cents", "transaction_count"}, ...]}
    约定：月份连续、空月补 0 由后端保证。返回 True/False 同饼图。
    """
    items = (data or {}).get("items") or []
    if not items:
        return False
    xs = [f"{int(i['month'][5:7])} 月" for i in items]
    ys = [cents_to_yuan(i.get("amount_cents") or 0) for i in items]
    counts = [i.get("transaction_count") or 0 for i in items]

    fig = go.Figure(go.Bar(
        x=xs, y=ys,
        marker=dict(color="#4A7BE8", line=dict(width=0)),
        customdata=counts,
        hovertemplate="%{x}<br>支出 ¥%{y:,.2f}（%{customdata} 笔）<extra></extra>",
    ))
    fig.update_layout(
        **_CHART_LAYOUT,
        height=340,
        bargap=0.45,
        xaxis=dict(showgrid=False, zeroline=False, showline=False),
        yaxis=dict(gridcolor="#EDF1F7", zeroline=False, showline=False, title=None),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    return True
