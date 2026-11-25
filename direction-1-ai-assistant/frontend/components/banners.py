# -*- coding: utf-8 -*-
"""
横幅（banner）组件：
  - budget_banner()：预算预警 banner，数据来自 GET /api/budgets/status；
      未设置 → 中性灰提示；<80% 正常蓝；80%~100% 黄色预警；≥100% 红色超支高亮。
  - budget_progress_html()：细进度条 HTML（banner 与侧边栏共用，颜色随等级变化）。
前端只做阈值判断与配色，不计算任何金额（金额均来自 api 层）。
"""

import config
import streamlit as st

from utils import cents_to_yuan, format_yuan


def budget_progress_html(ratio, level):
    """按执行比例与等级渲染一条细进度条 HTML。level: normal / warn / over / None。"""
    ratio = ratio or 0.0
    pct = min(max(ratio * 100, 0), 100)
    color = {"over": "#D9534F", "warn": "#E8A33D", "normal": "#4A7BE8"}.get(level, "#C6CEDD")
    return (f'<div class="ledger-progress">'
            f'<div style="width:{pct:.1f}%;background:{color};"></div>'
            f"</div>")


def budget_banner(status):
    """预算预警 banner。

    status 结构（GET /api/budgets/status 出参）：
      {"month": "YYYY-MM",
       "total": {"budget_cents", "spent_cents", "ratio", "level"}}

    展示规则（阈值见 config.py）：
      - 未设置预算（budget_cents=0）→ 中性灰提示；
      - ratio < 0.8            → 蓝色「预算执行良好」；
      - 0.8 ≤ ratio < 1.0      → 黄色预警「已使用 X%，请注意控制」；
      - ratio ≥ 1.0            → 红色超支高亮（含超支金额）。
    后端不返回 level 时，按 ratio 自行判断。
    """
    total = (status or {}).get("total") or {}
    budget = total.get("budget_cents") or 0
    spent = total.get("spent_cents") or 0
    ratio = total.get("ratio")
    level = total.get("level")

    if not budget:
        st.markdown(
            '<div class="ledger-banner ledger-banner-info">'
            f'<span class="b-strong">本月尚未设置预算</span>　本月支出 ¥{format_yuan(spent)}，'
            '可在下方表单中设置月度总预算。</div>',
            unsafe_allow_html=True)
        return

    if ratio is None:
        ratio = spent / budget
    if level not in ("normal", "warn", "over"):
        if ratio >= config.BUDGET_OVER_RATIO:
            level = "over"
        elif ratio >= config.BUDGET_WARN_RATIO:
            level = "warn"
        else:
            level = "normal"

    pct = ratio * 100
    if level == "over":
        over_yuan = max(spent - budget, 0) / 100
        text = (f'<span class="b-strong">本月已超支 ¥{over_yuan:,.2f}</span>'
                f'　预算 ¥{cents_to_yuan(budget):,.2f}，已支出 ¥{cents_to_yuan(spent):,.2f}'
                f'（{pct:.0f}%），请留意消费。')
        cls = "ledger-banner-over"
    elif level == "warn":
        text = (f'<span class="b-strong">本月预算已使用 {pct:.0f}%，请注意控制</span>'
                f'　预算 ¥{cents_to_yuan(budget):,.2f}，已支出 ¥{cents_to_yuan(spent):,.2f}。')
        cls = "ledger-banner-warn"
    else:
        text = (f'<span class="b-strong">预算执行良好</span>'
                f'　已使用 {pct:.0f}%，预算 ¥{cents_to_yuan(budget):,.2f}，'
                f'支出 ¥{cents_to_yuan(spent):,.2f}。')
        cls = "ledger-banner-normal"

    st.markdown(f'<div class="ledger-banner {cls}">{text}'
                f'{budget_progress_html(ratio, level)}</div>',
                unsafe_allow_html=True)
