# -*- coding: utf-8 -*-
"""
⑥ 预算预警 Section（接口契约 v1）：
  顶部预算执行 banner（GET /api/v1/budgets/{month} 适配）；
  下方预算设置表单（PUT /api/v1/budgets/{month}，金额为 0 时调用 DELETE 取消）；
  附「预算执行情况」明细表。

后端当前只支持月度总预算，分类预算暂不展示。
"""

import pandas as pd
import streamlit as st

from components.banners import budget_banner
from components.style import section_header
from services import api_client
from utils import current_month_key, shift_month_key, to_error_message

_PREFIX = "bgt"

_STATUS_LABELS = {"normal": "正常", "warning": "预警", "exceeded": "超支"}


def _load_budget(month):
    """读取某月预算；未设置（404）时返回空字典。"""
    try:
        return api_client.fetch_budgets(month) or {}
    except api_client.ApiError as exc:
        if exc.status_code == 404:
            return {}
        raise


def render(categories):
    section_header("⑥", "预算预警",
                   "设置月度总预算，超支前自动提醒（80% 黄色预警 / 100% 红色超支）。")

    month_key = current_month_key()
    month_options = [shift_month_key(month_key, -1), month_key, shift_month_key(month_key, 1)]

    # ── 预算执行 banner ──
    try:
        budget_banner(api_client.fetch_budget_status(month_key))
    except Exception as e:
        st.error(to_error_message(e))

    # ── 预算设置表单 ──
    s1, s2 = st.columns([1.2, 2])
    with s1:
        month = st.selectbox("预算月份", month_options, index=1,
                             key=f"{_PREFIX}_month",
                             format_func=lambda m: f"{m[:4]} 年 {int(m[5:7])} 月")
    with s2:
        st.write("")

    # 切换月份时用已保存预算回填；未设置则显示 0
    if st.session_state.get(f"{_PREFIX}_init_month") != month:
        try:
            saved = _load_budget(month)
        except Exception as e:
            st.error(to_error_message(e))
            saved = {}
        st.session_state[f"{_PREFIX}_init_month"] = month
        amount = saved.get("amount")
        st.session_state[f"{_PREFIX}_total"] = float(amount) if amount is not None else 0.0

    total_yuan = st.number_input("月度总预算（元，0 表示取消本月预算）",
                                 min_value=0.0, step=100.0, format="%.2f",
                                 key=f"{_PREFIX}_total")

    st.caption("当前仅支持月度总预算，分类预算后续版本再开放。")

    if st.button("保存预算设置", type="primary", key=f"{_PREFIX}_save"):
        with st.spinner("正在保存预算…"):
            try:
                api_client.save_budget(month, f"{total_yuan:.2f}")
                if total_yuan <= 0:
                    st.success(f"{month[:4]} 年 {int(month[5:7])} 月预算已取消 ✅")
                else:
                    st.success(f"{month[:4]} 年 {int(month[5:7])} 月预算已保存 ✅")
                st.rerun()
            except Exception as e:
                st.error(to_error_message(e))

    # ── 预算执行明细 ──
    with st.expander("查看预算执行情况"):
        try:
            data = _load_budget(month)
            if not data or float(data.get("amount") or 0) <= 0:
                st.info("该月尚未设置预算。")
            else:
                usage = float(data.get("usage_percent") or 0)
                rows = [{
                    "月份": data.get("month") or month,
                    "预算(元)": data.get("amount"),
                    "已支出(元)": data.get("spent"),
                    "剩余(元)": data.get("remaining"),
                    "使用率": f"{usage:.2f}%",
                    "状态": _STATUS_LABELS.get(data.get("status"), "正常"),
                }]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(to_error_message(e))
