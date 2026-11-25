# -*- coding: utf-8 -*-
"""
⑥ 预算预警 Section：
  顶部预算执行 banner（GET /api/budgets/status：<80% 蓝 / 80%~100% 黄预警 / ≥100% 红超支）；
  下方预算设置表单（PUT /api/budgets）：月度总预算 + 分类预算（元为单位，提交 ×100）；
  附「预算执行明细」折叠表（GET /api/budgets）。
"""

import pandas as pd
import streamlit as st

from components.banners import budget_banner
from components.style import section_header
from services import api_client
from utils import (current_month_key, format_yuan, shift_month_key,
                   to_error_message, yuan_to_cents)

_PREFIX = "bgt"


def render(categories):
    section_header("⑥", "预算预警",
                   "设置月度总预算与分类预算，超支前自动提醒（80% 黄色预警 / 100% 红色超支）。")

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

    # 切换到某月时：用已保存预算回填表单默认值（否则给演示默认值）
    if st.session_state.get(f"{_PREFIX}_init_month") != month:
        try:
            saved = api_client.fetch_budgets(month)
        except Exception:
            saved = {}
        st.session_state[f"{_PREFIX}_init_month"] = month
        # 注意：预算为 0（未设置）与 None（接口失败/缺字段）要区分——
        # 只有 None 才回退默认值，0 必须原样显示为「未设置」
        saved_total = saved.get("total_budget_cents")
        st.session_state[f"{_PREFIX}_total"] = (
            saved_total if saved_total is not None else 300000) / 100
        cat_saved = {i.get("category_id"): i.get("budget_cents", 0)
                     for i in (saved.get("items") or []) if i.get("category_id")}
        for c in categories:
            st.session_state[f"{_PREFIX}_cat_{c['id']}"] = (cat_saved.get(c["id"], 0) or 0) / 100

    total_yuan = st.number_input("月度总预算（元，0 表示不设置）",
                                 min_value=0.0, step=100.0, format="%.2f",
                                 key=f"{_PREFIX}_total")

    st.markdown("**分类预算（元，0 表示不设置）**")
    cat_budgets = []
    for row_start in range(0, len(categories), 3):
        cols = st.columns(3)
        for col, cat in zip(cols, categories[row_start:row_start + 3]):
            with col:
                v = st.number_input(cat["name"], min_value=0.0, step=50.0,
                                    format="%.2f", key=f"{_PREFIX}_cat_{cat['id']}")
                cat_budgets.append({"category_id": cat["id"],
                                    "budget_cents": yuan_to_cents(v)})

    if st.button("保存预算设置", type="primary", key=f"{_PREFIX}_save"):
        payload = {"month": month,
                   "total_budget_cents": yuan_to_cents(total_yuan),
                   "category_budgets": cat_budgets}
        with st.spinner("正在保存预算…"):
            try:
                api_client.save_budgets(payload)
                st.success(f"{month[:4]} 年 {int(month[5:7])} 月预算已保存 ✅")
                st.rerun()
            except Exception as e:
                st.error(to_error_message(e))

    # ── 预算执行明细（折叠表，数据来自 GET /api/budgets）──
    with st.expander("查看预算执行明细"):
        try:
            b = api_client.fetch_budgets(month_key)
            rows = []
            for i in (b.get("items") or []):
                budget = i.get("budget_cents") or 0
                ratio = i.get("ratio")
                rows.append({
                    "类别": i.get("category_name") or "—",
                    "预算(元)": format_yuan(budget) if budget else "未设置",
                    "已支出(元)": format_yuan(i.get("spent_cents") or 0),
                    "使用率": "—" if ratio is None else f"{ratio * 100:.0f}%",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(to_error_message(e))
