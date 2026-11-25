# -*- coding: utf-8 -*-
"""
日历视图（手搓极简月历）
========================
不使用第三方日历库：用 st.columns(7) + st.button 拼出 2026 年 11 月的
月度网格，并在下方展示选中日期的消费明细卡片。

Mock 数据写死在 MOCK_SPENDING，格式：
    {"2026-11-05": [{"amount": 50, "category": "餐饮", "note": "午饭"}, ...], ...}
"""

import calendar
import datetime

import streamlit as st

YEAR, MONTH = 2026, 11
WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")
CATEGORY_EMOJI = {
    "餐饮": "🍜", "交通": "🚕", "购物": "🛍️", "娱乐": "🎬",
    "居住": "🏠", "医疗": "💊", "教育": "📚", "其他": "💸",
}

# 固定 Mock 数据：11 笔，合计 ¥1,752.00，与侧边栏演示数据一致
MOCK_SPENDING = {
    "2026-11-02": [
        {"amount": 12, "category": "餐饮", "note": "早餐"},
        {"amount": 32, "category": "餐饮", "note": "咖啡"},
    ],
    "2026-11-05": [
        {"amount": 50, "category": "餐饮", "note": "午饭"},
        {"amount": 18, "category": "餐饮", "note": "奶茶"},
    ],
    "2026-11-08": [
        {"amount": 60, "category": "娱乐", "note": "电影"},
    ],
    "2026-11-11": [
        {"amount": 225, "category": "餐饮", "note": "火锅 AA 分摊"},
    ],
    "2026-11-15": [
        {"amount": 28, "category": "交通", "note": "打车"},
    ],
    "2026-11-18": [
        {"amount": 1200, "category": "居住", "note": "房租"},
    ],
    "2026-11-22": [
        {"amount": 64, "category": "购物", "note": "超市采购"},
    ],
    "2026-11-25": [
        {"amount": 45, "category": "医疗", "note": "感冒药"},
    ],
    "2026-11-28": [
        {"amount": 18, "category": "餐饮", "note": "奶茶"},
    ],
}

_CSS = """
<style>
/* 日历模式没有底部输入框，缩短主区域底部留白 */
[data-testid="stMainBlockContainer"]:has(.cal-title) {
  padding-bottom: 2.5rem !important;
}

.cal-title {
  font-size: 1.4rem; font-weight: 700; color: #111827; letter-spacing: -.01em;
}
.cal-sub { color: #8A93A6; font-size: .85rem; margin: .2rem 0 .9rem 0; }
.cal-sub b { color: #1F2937; }
.cal-weekday {
  text-align: center; color: #A0A7B4; font-size: .74rem;
  letter-spacing: .06em; padding: .2rem 0 .55rem 0;
}

/* 日历格子：用 key 前缀选择器覆盖聊天区的胶囊按钮样式 */
[data-testid="stMainBlockContainer"] [class*="st-key-calday_"] { width: 100% !important; }
[data-testid="stMainBlockContainer"] [class*="st-key-calday_"] .stButton { width: 100% !important; }
[data-testid="stMainBlockContainer"] [class*="st-key-calday_"] .stButton > button {
  width: 100% !important;
  height: 48px !important;
  min-height: 48px !important;
  border-radius: 12px !important;
  border: 1px solid #EEF1F6 !important;
  background: #FFFFFF !important;
  color: #374151 !important;
  font-size: .88rem !important;
  font-weight: 500 !important;
  padding: 0 !important;
  box-shadow: none !important;
}
[data-testid="stMainBlockContainer"] [class*="st-key-calday_"] .stButton > button:hover {
  border-color: #C9D8F7 !important;
  background: #F8FAFF !important;
  color: #2C5BB8 !important;
}
[data-testid="stMainBlockContainer"] [class*="st-key-calday_"] .stButton > button[kind="primary"] {
  background: #4A7BE8 !important;
  border-color: #4A7BE8 !important;
  color: #FFFFFF !important;
}
.cal-amount {
  text-align: center; color: #D9534F; font-size: .7rem;
  line-height: 1.1; height: 14px; margin-top: 2px;
  font-variant-numeric: tabular-nums;
}
.cal-amount-empty { visibility: hidden; }
.cal-empty-cell { height: 66px; }

.cal-divider { height: 1px; background: #EEF1F6; margin: 1.5rem 0 1.2rem 0; }
.cal-detail-title { font-size: 1.05rem; font-weight: 650; color: #111827; }
.cal-detail-sum { color: #8A93A6; font-size: .8rem; margin: .25rem 0 .8rem 0; }
.cal-card {
  display: flex; align-items: center; justify-content: space-between;
  background: #FFFFFF; border: 1px solid #EEF1F6; border-radius: 14px;
  padding: .7rem .95rem; margin-bottom: .5rem;
}
.cal-card-cat { font-size: .9rem; font-weight: 600; color: #1F2937; }
.cal-card-note { font-size: .76rem; color: #9CA3AF; margin-top: .1rem; }
.cal-card-amount {
  font-size: .9rem; font-weight: 600; color: #D9534F;
  font-variant-numeric: tabular-nums;
}
</style>
"""


def _month_total(spending) -> tuple:
    """返回 (总金额, 总笔数)。"""
    total = sum(item["amount"] for records in spending.values() for item in records)
    count = sum(len(records) for records in spending.values())
    return total, count


def _to_spending(records) -> dict:
    """把契约账目列表转成日历使用的 {YYYY-MM-DD: [{amount, category, note}]}。"""
    spending = {}
    for item in records or []:
        iso = str(item.get("spent_at") or "")[:10]
        if not iso:
            continue
        try:
            amount = float(item.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        spending.setdefault(iso, []).append({
            "amount": amount,
            "category": item.get("category") or "其他",
            "note": item.get("note") or "",
        })
    return spending


def _date_label(iso: str) -> str:
    try:
        parsed = datetime.date.fromisoformat(iso)
        return f"{parsed.month} 月 {parsed.day} 日"
    except ValueError:
        return iso


def render(records=None, year: int = YEAR, month: int = MONTH) -> None:
    """渲染手搓月历 + 选中日期的明细卡片。

    records=None 时使用内置 MOCK_SPENDING（演示模式）；
    否则使用传入的真实账目列表（契约字段 amount/spent_at/category/note）。
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    spending = MOCK_SPENDING if records is None else _to_spending(records)
    default_selected = f"{year:04d}-{month:02d}-05"
    selected = st.session_state.get("selected_date")
    if not isinstance(selected, str) or not selected.startswith(f"{year:04d}-{month:02d}-"):
        selected = default_selected
        st.session_state["selected_date"] = selected

    total, count = _month_total(spending)
    st.markdown(f'<div class="cal-title">📅 {year} 年 {month} 月</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div class="cal-sub">本月支出 <b>¥{total:,.2f}</b> · 共 {count} 笔消费</div>',
        unsafe_allow_html=True)

    # 星期表头（周一开头）
    header_cols = st.columns(7)
    for index, name in enumerate(WEEKDAYS):
        with header_cols[index]:
            st.markdown(f'<div class="cal-weekday">{name}</div>',
                        unsafe_allow_html=True)

    selected = st.session_state.get("selected_date", default_selected)
    first_weekday, days_in_month = calendar.monthrange(year, month)
    cells = [None] * first_weekday + list(range(1, days_in_month + 1))
    while len(cells) % 7:
        cells.append(None)

    clicked_date = None
    for week_start in range(0, len(cells), 7):
        cols = st.columns(7)
        for index in range(7):
            day = cells[week_start + index]
            with cols[index]:
                if day is None:
                    st.markdown('<div class="cal-empty-cell"></div>', unsafe_allow_html=True)
                    continue

                iso = f"{year:04d}-{month:02d}-{day:02d}"
                records = spending.get(iso, [])
                day_total = sum(item["amount"] for item in records)
                is_selected = iso == selected

                if st.button(
                    str(day),
                    key=f"calday_{iso}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    clicked_date = iso

                if day_total:
                    st.markdown(f'<div class="cal-amount">¥{day_total:,.0f}</div>',
                                unsafe_allow_html=True)
                else:
                    st.markdown('<div class="cal-amount cal-amount-empty">&nbsp;</div>',
                                unsafe_allow_html=True)

    if clicked_date:
        st.session_state.selected_date = clicked_date
        st.rerun()

    # ── 选中日期的消费明细 ──
    selected = st.session_state.get("selected_date", default_selected)
    records = spending.get(selected, [])
    st.markdown('<div class="cal-divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cal-detail-title">📌 {_date_label(selected)} 消费明细</div>',
                unsafe_allow_html=True)

    if not records:
        st.caption("这一天没有消费记录。")
        return

    day_total = sum(item["amount"] for item in records)
    st.markdown(
        f'<div class="cal-detail-sum">共 {len(records)} 笔 · ¥{day_total:,.2f}</div>',
        unsafe_allow_html=True)

    for item in records:
        emoji = CATEGORY_EMOJI.get(item["category"], "💸")
        st.markdown(
            '<div class="cal-card">'
            '<div>'
            f'<div class="cal-card-cat">{emoji} {item["category"]}</div>'
            f'<div class="cal-card-note">{item["note"]}</div>'
            '</div>'
            f'<div class="cal-card-amount">- ¥{item["amount"]:,.2f}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
