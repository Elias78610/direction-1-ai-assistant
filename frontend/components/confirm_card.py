# -*- coding: utf-8 -*-
"""
「解析 / OCR 识别」确认卡片组件（复用组件，F2 与 F3 共用）。

职责：把 api 层返回的草稿（draft）渲染成一张可编辑的卡片，
      用户核对/修改 方向、金额、日期、分类、商户、备注 后点「确认」。
      组件只负责收集与返回 payload，不发起任何网络请求（由页面调用 api 层）。

草稿结构（docs/需求与接口梳理.md 3.3 / 3.6）：
  draft = {"amount_cents", "occurred_at", "direction", "category_id",
           "category_name", "merchant", "note", "confidence"}
"""

import config
import streamlit as st

from utils import cents_to_yuan, parse_iso_date, today, yuan_to_cents

_DIRECTION_KEYS = {"支出": "expense", "收入": "income"}

# 卡片持有的会话状态键（前缀区分不同卡片，避免同页多卡片互相干扰）
_CARD_KEYS = ("_draft", "_marker", "_direction", "_amount_yuan", "_date",
              "_category", "_merchant", "_note", "_dup")


def set_draft(prefix, draft):
    """页面在拿到新草稿后调用：写入状态并清空标记，触发卡片重新初始化。"""
    st.session_state[f"{prefix}_draft"] = draft
    st.session_state[f"{prefix}_marker"] = ""
    st.session_state[f"{prefix}_dup"] = False


def clear_draft(prefix):
    """清空确认卡片状态（提交成功或点「放弃」后调用，配合 st.rerun()）。"""
    for k in _CARD_KEYS:
        st.session_state.pop(prefix + k, None)


def _init_state(prefix, draft):
    """首次渲染（或换了新草稿）时，把草稿值写入各控件的默认值。"""
    d = draft or {}
    st.session_state[f"{prefix}_marker"] = _marker_of(draft)
    st.session_state[f"{prefix}_direction"] = "收入" if d.get("direction") == "income" else "支出"
    st.session_state[f"{prefix}_amount_yuan"] = cents_to_yuan(d.get("amount_cents") or 0)
    st.session_state[f"{prefix}_date"] = parse_iso_date(d.get("occurred_at")) or today()
    st.session_state[f"{prefix}_category"] = d.get("category_id") or None
    st.session_state[f"{prefix}_merchant"] = d.get("merchant") or ""
    st.session_state[f"{prefix}_note"] = d.get("note") or ""


def _marker_of(draft):
    """草稿指纹：用于判断是否需要重新初始化编辑默认值。"""
    return repr(sorted((draft or {}).items(), key=lambda kv: str(kv[0])))


def render_draft_card(prefix, draft, categories, submit_label="确认入库",
                      raw_text=None, raw_label="原始输入",
                      warnings=None, duplicate_hint=False):
    """渲染可编辑确认卡片。

    参数：
      prefix         状态键前缀（如 "nl" / "ocr"）
      draft          api 层返回的草稿 dict
      categories     分类列表 [{"id", "name"}]（来自 GET /api/categories）
      submit_label   确认按钮文案
      raw_text       （可选）原始输入 / OCR 原文，折叠展示
      raw_label      折叠区标题
      warnings       （可选）后端提示列表（如「金额识别不确定，请核对」）
      duplicate_hint （可选）疑似重复标记，为 True 时需勾选确认才能提交

    返回：
      None  用户未点确认（或条件不满足）
      dict  确认后的 payload：{amount_cents, occurred_at, direction,
             category_id, merchant, note}
            （source / raw_input / confidence / receipt_id 由调用方补充）
    """
    if not draft:
        return None

    # 1) 草稿换了 → 重新初始化编辑默认值
    if st.session_state.get(f"{prefix}_marker") != _marker_of(draft):
        _init_state(prefix, draft)

    # 2) 原始输入 / OCR 原文折叠区
    if raw_text:
        with st.expander(raw_label):
            st.text(raw_text)

    # 3) 低置信度黄色提示（阈值见 config.py：低于 0.7 提示复核）
    confidence = draft.get("confidence")
    if confidence is not None and confidence < config.CONFIDENCE_WARN_THRESHOLD:
        st.markdown(
            f'<span class="ledger-note-low">⚠️ AI 置信度 {confidence:.0%}，'
            '识别结果可能不准确，请核对后再确认。</span>',
            unsafe_allow_html=True)

    # 4) 后端 warnings
    for w in (warnings or []):
        st.warning(w)

    # 5) 可编辑字段：方向 / 金额 / 日期 / 分类 / 商户 / 备注
    c1, c2, c3 = st.columns([1, 1.1, 1.1])
    with c1:
        direction_label = st.radio("收支方向", ["支出", "收入"],
                                   key=f"{prefix}_direction", horizontal=True)
    with c2:
        amount_yuan = st.number_input("金额（元）", min_value=0.0, step=0.01,
                                      format="%.2f", key=f"{prefix}_amount_yuan")
    with c3:
        occurred = st.date_input("消费日期", key=f"{prefix}_date")

    c4, c5 = st.columns([1, 1.4])
    with c4:
        cat_labels = {None: "未识别（请选择）"}
        cat_labels.update({c["id"]: c["name"] for c in categories})
        category_id = st.selectbox(
            "分类", [None] + [c["id"] for c in categories],
            key=f"{prefix}_category",
            format_func=lambda x: cat_labels.get(x, "—"))
    with c5:
        merchant = st.text_input("商户", key=f"{prefix}_merchant")

    note = st.text_input("备注（可选）", key=f"{prefix}_note")

    # 6) 疑似重复确认（后端 duplicate_hint=True 时出现，勾选后才能提交）
    dup_checked = True
    if duplicate_hint:
        st.warning("该笔流水疑似重复（相同日期/金额/商户），请确认是否仍要添加。")
        dup_checked = st.checkbox("我确认仍要添加这笔流水", key=f"{prefix}_dup")

    # 7) 操作按钮
    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        submitted = st.button(submit_label, type="primary",
                              key=f"{prefix}_submit",
                              disabled=not dup_checked,
                              use_container_width=True)
    with b2:
        cancelled = st.button("放弃", key=f"{prefix}_cancel", use_container_width=True)

    if cancelled:
        clear_draft(prefix)
        st.rerun()

    if submitted:
        if amount_yuan is None or amount_yuan <= 0:
            st.error("请填写大于 0 的金额。")
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
