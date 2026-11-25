# -*- coding: utf-8 -*-
"""
④ 消费图表 Section：
  分类占比环形图（GET /api/stats/category）+ 月度趋势柱状图（GET /api/stats/monthly）。
  数据全部来自 api 层统计接口，前端不做金额计算；空数据显示占位文案。
"""

from datetime import date

import streamlit as st

from components.charts import render_category_pie, render_monthly_bar
from components.style import section_header
from services import api_client
from utils import parse_iso_date, range_for_preset, to_error_message

_PRESETS = ["本月", "上月", "近3月", "近6月", "全部", "自定义"]


def render():
    section_header("④", "消费图表",
                   "分类占比与月度趋势一目了然，图表数据均来自后端统计接口。")

    f1, f2 = st.columns([1.6, 1.2])
    with f1:
        preset = st.selectbox("统计范围", _PRESETS, key="chart_preset")
    start, end = range_for_preset(preset)
    if preset == "自定义":
        c_s, c_e = st.columns(2)
        with c_s:
            start = st.date_input("开始日期",
                                  value=parse_iso_date(start) or date.today(),
                                  key="chart_start").isoformat()
        with c_e:
            end = st.date_input("结束日期",
                                value=parse_iso_date(end) or date.today(),
                                key="chart_end").isoformat()
    with f2:
        months = st.selectbox("趋势月数", [6, 12], key="chart_months")

    # 左：分类占比饼图；右：月度趋势柱状图
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**消费分类占比**")
        try:
            cat_data = api_client.fetch_stats_category(start_date=start, end_date=end)
            if not render_category_pie(cat_data):
                st.info("所选范围内暂无支出数据。")
        except Exception as e:
            st.error(to_error_message(e))

    with right:
        st.markdown("**月度消费趋势**")
        try:
            monthly_data = api_client.fetch_stats_monthly(months=months)
            if not render_monthly_bar(monthly_data):
                st.info("暂无月度数据。")
        except Exception as e:
            st.error(to_error_message(e))
