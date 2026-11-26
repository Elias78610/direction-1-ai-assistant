# -*- coding: utf-8 -*-
"""
左侧边栏（对话 / 日历 / 统计 三模式）
====================================
结构：
  1. Logo / 标题
  2. 模式切换：💬 对话 / 📅 日历 / 📊 统计（st.radio）
  3. 本月预算进度（原生 st.progress）
  4. 历史会话列表（st.button + 无边框样式模拟文字列表）
  5. 底部面板：⚙️ 高级设置 st.expander（后端地址 / 演示模式 / 预算模拟 slider）
     + 🎨 用户气泡颜色 st.color_picker

预算数字暂时来自 app.py 的演示数据；模拟使用率会写入
st.session_state["budget_ratio_pct"]，由 app.py 换算成 budget_ratio。
"""

import streamlit as st

import config
from components import budget_settings, custom_style

VIEW_MODES = ("💬 对话", "📅 日历", "📊 统计")


def render_sidebar(sessions, current_id, spent, budget, demo_mode=True,
                   budget_missing=False):
    """渲染侧边栏并返回用户的导航操作。

    参数：
        sessions:   会话列表 [{"id", "title", "messages"}, ...]
        current_id: 当前会话 id
        spent:      本月已支出（元）
        budget:     本月预算（元）
        demo_mode:  True 时显示可拖动模拟滑块；False 时滑块锁定
        budget_missing: 真实模式未设置预算
    """
    new_chat = False
    selected = None

    st.session_state.setdefault("view_mode", VIEW_MODES[0])
    st.session_state.setdefault("budget_ratio_pct", 85)

    with st.sidebar:
        # ── 1. Logo / 标题 ──
        st.markdown('<div class="sb-brand">📒 记账 AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-tagline">你的智能消费管家</div>', unsafe_allow_html=True)

        # ── 2. 对话 / 日历 / 统计模式切换 ──
        st.radio(
            "模式",
            VIEW_MODES,
            key="view_mode",
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown('<div class="sb-divider" style="margin:.55rem 0 .2rem 0;"></div>',
                    unsafe_allow_html=True)

        # ── 3. 本月预算进度（原生 st.progress）──
        st.markdown('<div class="sb-label">本月预算</div>', unsafe_allow_html=True)
        ratio = (spent / budget) if budget else 0.0
        st.progress(min(max(ratio, 0.0), 1.0))
        if budget_missing:
            st.markdown(
                '<div class="sb-budget-meta">本月未设置预算</div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="sb-budget-meta">已用 {ratio * 100:.0f}% · '
                f'¥{spent:,.0f} / ¥{budget:,.0f}</div>',
                unsafe_allow_html=True)

        # 预算设置入口；真实模式写后端，演示模式只改当前会话。
        budget_settings.render(demo_mode=demo_mode, current_budget=budget)

        # ── 4. 历史会话（无边框按钮列表）──
        st.markdown('<div class="sb-label">历史会话</div>', unsafe_allow_html=True)

        if st.button("＋  新对话", key="new_chat", use_container_width=True, type="primary"):
            new_chat = True

        for session in reversed(sessions):
            is_active = session["id"] == current_id
            label = ("● " if is_active else "　") + session["title"]
            if st.button(label, key=f"session_{session['id']}", use_container_width=True):
                selected = session["id"]

        # ── 5. 底部面板：高级设置 + 用户气泡颜色 ──
        with st.container(key="sidebar_bottom_panel"):
            with st.expander("⚙️ 高级设置"):
                st.text_input("后端地址", key="api_base_url", disabled=True)
                demo_mode = st.toggle(
                    "演示模式（DEMO）",
                    value=demo_mode,
                    key="demo_mode",
                )

                # 演示模式：模拟预算使用率；真实模式由后端预算决定。
                st.slider(
                    "模拟预算使用率",
                    min_value=0,
                    max_value=120,
                    step=5,
                    key="budget_ratio_pct",
                    format="%d%%",
                    disabled=not demo_mode,
                    help="演示模式用于测试情绪小球与超支警告；真实模式锁定为后端 usage_percent",
                )
                if demo_mode:
                    st.caption("拖动可测试情绪小球和超支警告")
                else:
                    st.caption("真实模式：预算/使用率来自 GET /api/v1/budgets/{month}")

                st.caption(f"后端地址固定：{config.API_BASE_URL}")

            custom_style.render_color_picker()

    return new_chat, selected
