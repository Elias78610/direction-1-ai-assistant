# -*- coding: utf-8 -*-
"""
③ 流水列表 Section：
  时间范围（本月/上月/近3月/近6月/全部/自定义）+ 分类 + 方向筛选
  → GET /api/transactions 列表展示；
  选择某笔流水 → 编辑表单（PUT /api/transactions/{id}）；
  删除需二次确认（DELETE /api/transactions/{id}）。
金额展示为元（÷100），单位标注在列名上。
"""

from datetime import date

import pandas as pd
import streamlit as st

from components.style import section_header
from services import api_client
from utils import (format_yuan, parse_iso_date, range_for_preset,
                   to_error_message, yuan_to_cents)

_PREFIX = "tx"
_PRESETS = ["本月", "上月", "近3月", "近6月", "全部", "自定义"]
_SOURCE_LABELS = {"text": "自然语言", "receipt": "小票OCR", "manual": "手动"}
_DIRECTION_LABELS = {"expense": "支出", "income": "收入"}
_DIRECTION_KEYS = {"支出": "expense", "收入": "income"}


def render(categories):
    section_header("③", "流水列表",
                   "查看全部流水，支持时间范围 / 分类 / 方向筛选，可编辑与删除。")

    # ── 筛选器 ──
    f1, f2, f3 = st.columns([1.2, 1.2, 1.4])
    with f1:
        preset = st.selectbox("时间范围", _PRESETS, key=f"{_PREFIX}_preset")
    start, end = range_for_preset(preset)
    if preset == "自定义":
        c_s, c_e = st.columns(2)
        with c_s:
            start = st.date_input("开始日期",
                                  value=parse_iso_date(start) or date.today(),
                                  key=f"{_PREFIX}_start").isoformat()
        with c_e:
            end = st.date_input("结束日期",
                                value=parse_iso_date(end) or date.today(),
                                key=f"{_PREFIX}_end").isoformat()
    with f2:
        direction = st.selectbox("收支方向", ["全部", "支出", "收入"],
                                 key=f"{_PREFIX}_direction")
    with f3:
        cat_labels = {None: "全部分类"}
        cat_labels.update({c["id"]: c["name"] for c in categories})
        category_id = st.selectbox("分类", [None] + [c["id"] for c in categories],
                                   key=f"{_PREFIX}_category",
                                   format_func=lambda x: cat_labels.get(x, "—"))

    try:
        data = api_client.fetch_transactions(
            start_date=start, end_date=end,
            category_id=category_id,
            direction=None if direction == "全部" else _DIRECTION_KEYS[direction],
            limit=200, offset=0)
    except Exception as e:
        st.error(to_error_message(e))
        return

    txs = data.get("transactions") or []
    if not txs:
        st.info("当前筛选条件下暂无流水记录，先去记一笔吧。")
        return

    st.caption(f"共 {data.get('total', len(txs))} 笔流水（按日期倒序）")

    df = pd.DataFrame([
        {
            "日期": t["occurred_at"],
            "方向": _DIRECTION_LABELS.get(t["direction"], t["direction"]),
            "分类": t.get("category_name") or "—",
            "商户": t.get("merchant") or "—",
            "金额(元)": format_yuan(t["amount_cents"]),
            "来源": _SOURCE_LABELS.get(t.get("source"), t.get("source")),
            "备注": t.get("note") or "",
        } for t in txs
    ])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 height=min(36 + 35 * len(df), 420))

    # ── 编辑 / 删除 ──
    with st.expander("编辑 / 删除流水"):
        options = [t["id"] for t in txs]
        # 防止旧选择因列表变化失效（如刚删掉该笔）导致控件异常
        if st.session_state.get(f"{_PREFIX}_sel") not in options:
            st.session_state[f"{_PREFIX}_sel"] = options[0]
        labels = {t["id"]: f"{t['occurred_at']} · {t.get('merchant') or '（无商户）'} · "
                           f"¥{format_yuan(t['amount_cents'])}"
                  for t in txs}
        sel = st.selectbox("选择要操作的流水", options, key=f"{_PREFIX}_sel",
                           format_func=lambda x: labels.get(x, ""))
        _render_edit_form(sel, txs, categories)


def _render_edit_form(tx_id, txs, categories):
    """编辑/删除表单：选择变化时用该笔当前值刷新表单默认值。"""
    tx = next((t for t in txs if t["id"] == tx_id), None)
    if tx is None:
        return

    if st.session_state.get(f"{_PREFIX}_edit_marker") != tx_id:
        st.session_state[f"{_PREFIX}_edit_marker"] = tx_id
        st.session_state[f"{_PREFIX}_e_direction"] = "支出" if tx.get("direction") == "expense" else "收入"
        st.session_state[f"{_PREFIX}_e_amount"] = tx.get("amount_cents", 0) / 100
        st.session_state[f"{_PREFIX}_e_date"] = parse_iso_date(tx.get("occurred_at")) or date.today()
        st.session_state[f"{_PREFIX}_e_category"] = tx.get("category_id")
        st.session_state[f"{_PREFIX}_e_merchant"] = tx.get("merchant") or ""
        st.session_state[f"{_PREFIX}_e_note"] = tx.get("note") or ""
        st.session_state[f"{_PREFIX}_del_confirm"] = False

    st.markdown(f"**编辑 #{tx_id}**　·　来源："
                f"{_SOURCE_LABELS.get(tx.get('source'), tx.get('source'))}")

    e1, e2, e3 = st.columns([1, 1.1, 1.1])
    with e1:
        direction_label = st.radio("方向", ["支出", "收入"],
                                   key=f"{_PREFIX}_e_direction", horizontal=True)
    with e2:
        amount_yuan = st.number_input("金额（元）", min_value=0.0, step=0.01,
                                      format="%.2f", key=f"{_PREFIX}_e_amount")
    with e3:
        occurred = st.date_input("消费日期", key=f"{_PREFIX}_e_date")

    c4, c5 = st.columns([1, 1.4])
    with c4:
        cat_labels = {None: "未分类"}
        cat_labels.update({c["id"]: c["name"] for c in categories})
        category_id = st.selectbox("分类", [None] + [c["id"] for c in categories],
                                   key=f"{_PREFIX}_e_category",
                                   format_func=lambda x: cat_labels.get(x, "—"))
    with c5:
        merchant = st.text_input("商户", key=f"{_PREFIX}_e_merchant")
    note = st.text_input("备注", key=f"{_PREFIX}_e_note")

    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        save = st.button("保存修改", type="primary", key=f"{_PREFIX}_e_save",
                         use_container_width=True)
    with b2:
        confirmed = st.checkbox("确认删除", key=f"{_PREFIX}_del_confirm")
    with b3:
        delete = st.button("删除这笔流水", key=f"{_PREFIX}_e_delete",
                           disabled=not confirmed, use_container_width=True)

    if save:
        if amount_yuan is None or amount_yuan <= 0:
            st.error("请填写大于 0 的金额。")
        else:
            payload = {
                "amount_cents": yuan_to_cents(amount_yuan),
                "occurred_at": occurred.strftime("%Y-%m-%d"),
                "direction": _DIRECTION_KEYS.get(direction_label, "expense"),
                "category_id": category_id,
                "merchant": (merchant or "").strip(),
                "note": (note or "").strip(),
            }
            with st.spinner("正在保存修改…"):
                try:
                    api_client.update_transaction(tx_id, payload)
                    st.success("修改已保存 ✅")
                    st.session_state[f"{_PREFIX}_edit_marker"] = None
                    st.rerun()
                except Exception as e:
                    st.error(to_error_message(e))

    if delete:
        with st.spinner("正在删除…"):
            try:
                api_client.delete_transaction(tx_id)
                st.success("流水已删除 ✅")
                st.session_state[f"{_PREFIX}_edit_marker"] = None
                st.rerun()
            except Exception as e:
                st.error(to_error_message(e))
