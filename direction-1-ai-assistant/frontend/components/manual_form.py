# -*- coding: utf-8 -*-
"""
手动录入表单组件（解析 / OCR 失败时的降级路径，source="manual"）。

所有字段由用户自行填写，不含任何 AI / 后端逻辑；
提交后由页面调用 api 层 create_transaction 保存。
"""

import streamlit as st

from utils import today, yuan_to_cents

_DIRECTION_KEYS = {"支出": "expense", "收入": "income"}


def _init(prefix, default_note=""):
    """首次渲染时写入各控件默认值。"""
    st.session_state[f"{prefix}_mf_init"] = True
    st.session_state[f"{prefix}_mf_direction"] = "支出"
    st.session_state[f"{prefix}_mf_amount"] = 0.0
    st.session_state[f"{prefix}_mf_date"] = today()
    st.session_state[f"{prefix}_mf_category"] = None
    st.session_state[f"{prefix}_mf_merchant"] = ""
    st.session_state[f"{prefix}_mf_note"] = default_note


def clear_manual_form(prefix):
    """提交成功后清空表单状态（配合 st.rerun()）。"""
    for k in list(st.session_state.keys()):
        if k.startswith(f"{prefix}_mf_"):
            del st.session_state[k]


def render_manual_form(prefix, categories, default_note=""):
    """渲染手动录入表单。

    返回：None（未提交）或 payload dict
      {amount_cents, occurred_at, direction, category_id, merchant, note}
    （source 由调用方补充为 "manual"；raw_input / confidence / receipt_id 传 None）
    """
    if not st.session_state.get(f"{prefix}_mf_init"):
        _init(prefix, default_note)

    c1, c2, c3 = st.columns([1, 1.1, 1.1])
    with c1:
        direction_label = st.radio("收支方向", ["支出", "收入"],
                                   key=f"{prefix}_mf_direction", horizontal=True)
    with c2:
        amount_yuan = st.number_input("金额（元）", min_value=0.0, step=0.01,
                                      format="%.2f", key=f"{prefix}_mf_amount")
    with c3:
        occurred = st.date_input("消费日期", key=f"{prefix}_mf_date")

    c4, c5 = st.columns([1, 1.4])
    with c4:
        cat_labels = {None: "请选择分类"}
        cat_labels.update({c["id"]: c["name"] for c in categories})
        category_id = st.selectbox(
            "分类", [None] + [c["id"] for c in categories],
            key=f"{prefix}_mf_category",
            format_func=lambda x: cat_labels.get(x, "—"))
    with c5:
        merchant = st.text_input("商户", key=f"{prefix}_mf_merchant")

    note = st.text_input("备注（可选）", key=f"{prefix}_mf_note")

    submitted = st.button("保存这笔流水", type="primary", key=f"{prefix}_mf_submit")
    if submitted:
        if amount_yuan is None or amount_yuan <= 0:
            st.error("请填写大于 0 的金额。")
            return None
        if category_id is None:
            st.error("请选择分类。")
            return None
        return {
            "amount_cents": yuan_to_cents(amount_yuan),
            "occurred_at": occurred.strftime("%Y-%m-%d"),
            "direction": _DIRECTION_KEYS.get(direction_label, "expense"),
            "category_id": category_id,
            "merchant": (merchant or "").strip(),
            "note": (note or "").strip(),
        }
    return None
