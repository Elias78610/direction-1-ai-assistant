# -*- coding: utf-8 -*-
"""
预算设置（只属于预算模块）
==========================
- 真实模式：GET /api/v1/budgets/{month} 回填，PUT 保存；金额 0 走 DELETE 取消。
- 演示模式：只修改当前会话的模拟预算，不请求后端。
- 不修改全局 CSS、聊天布局、记账/流水/统计/OCR 等其他模块。
"""

import streamlit as st

from services import api_client
from utils import current_month_key, shift_month_key, to_error_message


def _month_label(month: str) -> str:
    return f"{month[:4]} 年 {int(month[5:7])} 月"


def _notice() -> None:
    notice = st.session_state.pop("_budget_setting_notice", None)
    if notice:
        st.success(notice)


def _render_demo(current_budget: float) -> None:
    st.caption("演示模式：预算金额只保存在当前会话，不写后端。")
    if "budget_setting_demo_amount" not in st.session_state:
        st.session_state["budget_setting_demo_amount"] = round(
            float(current_budget or 0), 2)
    amount = st.number_input(
        "月度总预算（元，0 表示取消）",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="budget_setting_demo_amount",
    )
    if st.button("保存预算", key="budget_setting_demo_save",
                 type="primary", use_container_width=True):
        st.session_state["demo_budget_amount"] = round(float(amount), 2)
        st.session_state["_budget_setting_notice"] = (
            "本月预算已取消（演示）。" if amount <= 0
            else f"本月预算已保存为 ¥{amount:,.2f}（演示）。"
        )
        st.rerun()


def _load_saved_amount(month: str) -> float:
    """读取某月已保存预算；未设置返回 0。"""
    try:
        data = api_client.fetch_budgets(month) or {}
        return round(float(data.get("amount") or 0), 2)
    except api_client.ApiError as exc:
        if exc.status_code == 404:
            return 0.0
        st.error(to_error_message(exc))
    except Exception as exc:
        st.error(to_error_message(exc))
    return 0.0


def _render_real() -> None:
    month_key = current_month_key()
    month_options = [shift_month_key(month_key, -1), month_key,
                     shift_month_key(month_key, 1)]
    month = st.selectbox(
        "预算月份",
        month_options,
        index=1,
        format_func=_month_label,
        key="budget_setting_month",
    )

    if st.session_state.get("budget_setting_loaded_month") != month:
        st.session_state["budget_setting_real_amount"] = _load_saved_amount(month)
        st.session_state["budget_setting_loaded_month"] = month

    amount = st.number_input(
        "月度总预算（元，0 表示取消）",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="budget_setting_real_amount",
    )

    if st.button("保存预算", key="budget_setting_real_save",
                 type="primary", use_container_width=True):
        try:
            api_client.save_budget(month, f"{amount:.2f}")
            st.session_state["_budget_setting_notice"] = (
                f"{_month_label(month)}预算已取消。"
                if amount <= 0
                else f"{_month_label(month)}预算已保存为 ¥{amount:,.2f}。"
            )
            st.rerun()
        except Exception as exc:
            st.error(to_error_message(exc))


def render(demo_mode: bool, current_budget: float) -> None:
    """侧边栏预算设置入口；展开后才显示表单。"""
    with st.expander("⚙️ 预算设置", expanded=False):
        _notice()
        if demo_mode:
            _render_demo(current_budget)
        else:
            _render_real()
