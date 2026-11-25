# -*- coding: utf-8 -*-
"""
⑤ 自然语言查账 Section：
  对话式提问 → POST /api/query → 展示文字回答（answer）+ 统计表格（table）。
  约定：数字一律来自后端返回的表格数据，前端只负责展示，绝不自行计算金额；
  保留最近 6 轮问答作为简单对话历史展示。
"""

import pandas as pd
import streamlit as st

from components.style import section_header
from services import api_client
from utils import to_error_message

_PREFIX = "qa"
_EXAMPLES = ["这个月吃饭花了多少", "本月交通支出", "这个月购物花了多少钱"]
_COLUMN_NAMES = {"category_name": "分类", "amount_cents": "金额(元)",
                 "transaction_count": "笔数"}


def render():
    section_header("⑤", "自然语言查账",
                   "像聊天一样问账本：AI 文字回答 + 统计明细表格，数字全部来自后端统计。")

    history = st.session_state.setdefault(f"{_PREFIX}_history", [])

    # ── 示例问题快捷按钮（点一下填入输入框）──
    c1, c2, c3 = st.columns(3)
    for col, q in zip((c1, c2, c3), _EXAMPLES):
        with col:
            if st.button(q, key=f"{_PREFIX}_ex_{q}", use_container_width=True):
                st.session_state[f"{_PREFIX}_input"] = q
                st.rerun()

    # ── 提问输入行 ──
    i1, i2 = st.columns([4, 1])
    with i1:
        question = st.text_input("问点什么", key=f"{_PREFIX}_input",
                                 label_visibility="collapsed",
                                 placeholder="例：这个月吃饭花了多少？")
    with i2:
        ask = st.button("查询", type="primary", key=f"{_PREFIX}_ask",
                        use_container_width=True)

    if ask:
        if not (question or "").strip():
            st.warning("请先输入要查询的问题。")
        else:
            with st.spinner("AI 正在查账…"):
                try:
                    result = api_client.query_accounts(question.strip())
                    history.append({"q": question.strip(),
                                    "a": result.get("answer", ""),
                                    "table": result.get("table")})
                    history[:] = history[-6:]  # 只保留最近 6 轮，保持页面整洁
                    st.session_state[f"{_PREFIX}_input"] = ""
                    st.rerun()
                except Exception as e:
                    st.error(to_error_message(e))

    # ── 历史问答（对话气泡样式）──
    if not history:
        st.info("还没有提问记录，试试上面的示例问题吧。")
        return

    for idx, item in enumerate(reversed(history)):
        st.markdown(
            f'<div class="ledger-qa">'
            f'<div class="ledger-q">{item["q"]}</div>'
            f'<div class="ledger-a">{item["a"]}</div>'
            f'</div>',
            unsafe_allow_html=True)
        tbl = item.get("table")
        if tbl:
            columns, rows = tbl.get("columns") or [], tbl.get("rows") or []
            if columns and rows:
                df = pd.DataFrame(rows, columns=columns)
                # 金额列（分）→ 展示为元
                for col in columns:
                    if "amount" in col or "cents" in col:
                        df[col] = df[col].apply(lambda v: f"¥{v / 100:,.2f}")
                df.columns = [_COLUMN_NAMES.get(c, c) for c in df.columns]
                st.dataframe(df, use_container_width=True, hide_index=True)
        if idx < len(history) - 1:
            st.markdown("---")
