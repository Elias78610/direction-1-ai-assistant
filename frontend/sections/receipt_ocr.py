# -*- coding: utf-8 -*-
"""
② 小票 OCR 上传 Section：
  st.file_uploader 上传小票图片 → 上传即识别（POST /api/receipts/ocr，长超时）
  → 校对卡片（可编辑 + OCR 原文折叠区 + 低置信度/warnings 提示）
  → POST /api/transactions（source="receipt"，带 receipt_id）保存；
  识别失败 → 黄色降级提示 + 手动录入表单。
"""

import streamlit as st

from components.confirm_card import clear_draft, render_draft_card, set_draft
from components.manual_form import clear_manual_form, render_manual_form
from components.style import section_header
from services import api_client
from utils import to_error_message

_PREFIX = "ocr"


def render(categories):
    section_header("②", "小票 OCR 上传",
                   "拍张购物小票，AI 自动识别金额与商户；识别结果可先校对再保存。")

    if not categories:
        st.info("分类列表加载失败，请检查后端服务后刷新页面。")
        return

    uploaded = st.file_uploader(
        "上传小票图片（jpg / png / webp，≤10MB）",
        type=["jpg", "jpeg", "png", "webp"], key=f"{_PREFIX}_uploader")

    if uploaded is None and st.session_state.get(f"{_PREFIX}_done_marker"):
        # 用户移除了已上传的图片：清掉旧的识别状态与标记（重传同一张图可重新识别）
        _reset_all()

    # ── 上传即识别：用「文件名:大小」做标记，同一张图只识别一次 ──
    if uploaded is not None:
        file_marker = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get(f"{_PREFIX}_done_marker") != file_marker:
            with st.spinner("正在识别小票（可能需要十几秒）…"):
                try:
                    result = api_client.ocr_receipt(uploaded.getvalue(), uploaded.name)
                    st.session_state[f"{_PREFIX}_done_marker"] = file_marker
                    st.session_state[f"{_PREFIX}_fallback"] = False
                    set_draft(_PREFIX, result["draft"])
                    st.session_state[f"{_PREFIX}_receipt_id"] = result.get("receipt_id")
                    st.session_state[f"{_PREFIX}_ocr_raw"] = result.get("ocr_raw", "")
                    st.session_state[f"{_PREFIX}_warnings"] = result.get("warnings") or []
                    st.session_state[f"{_PREFIX}_dup_hint"] = bool(result.get("duplicate_hint"))
                    st.session_state[f"{_PREFIX}_confidence"] = result["draft"].get("confidence")
                except Exception as e:
                    st.session_state[f"{_PREFIX}_done_marker"] = file_marker
                    clear_draft(_PREFIX)  # 清掉旧图草稿，避免与降级表单同屏混淆
                    st.session_state[f"{_PREFIX}_fallback"] = True
                    st.error(to_error_message(e))

        # 图片预览（半宽，避免占用过多空间）
        c_img, _ = st.columns([1, 2])
        with c_img:
            st.image(uploaded, caption=uploaded.name, use_container_width=True)

    # ── 识别成功 → 校对卡片 ──
    draft = st.session_state.get(f"{_PREFIX}_draft")
    if draft and not st.session_state.get(f"{_PREFIX}_fallback"):
        st.caption("识别草稿如下，请核对/修改后确认保存：")
        payload = render_draft_card(
            _PREFIX, draft, categories,
            submit_label="确认保存",
            raw_text=st.session_state.get(f"{_PREFIX}_ocr_raw"),
            raw_label="OCR 原始识别文本",
            warnings=st.session_state.get(f"{_PREFIX}_warnings"),
            duplicate_hint=bool(st.session_state.get(f"{_PREFIX}_dup_hint")),
        )
        if payload:
            payload["source"] = "receipt"
            payload["raw_input"] = st.session_state.get(f"{_PREFIX}_ocr_raw", "")
            payload["confidence"] = st.session_state.get(f"{_PREFIX}_confidence")
            payload["receipt_id"] = st.session_state.get(f"{_PREFIX}_receipt_id")
            with st.spinner("正在保存流水…"):
                try:
                    api_client.create_transaction(payload)
                    st.success("小票流水已保存 ✅")
                    _reset_all()
                    st.rerun()
                except Exception as e:
                    st.error(to_error_message(e))

    # ── 识别失败 → 降级手动录入 ──
    if st.session_state.get(f"{_PREFIX}_fallback"):
        st.markdown(
            '<div class="ledger-banner ledger-banner-warn">'
            '小票识别未成功，可改用手动录入，账本功能不受影响。</div>',
            unsafe_allow_html=True)
        with st.expander("手动录入表单", expanded=True):
            mpayload = render_manual_form(f"{_PREFIX}_mf", categories)
            if mpayload:
                mpayload["source"] = "manual"
                mpayload["raw_input"] = None
                mpayload["confidence"] = None
                mpayload["receipt_id"] = None
                with st.spinner("正在保存…"):
                    try:
                        api_client.create_transaction(mpayload)
                        st.success("已手动记一笔 ✅")
                        _reset_all()
                        st.rerun()
                    except Exception as e:
                        st.error(to_error_message(e))


def _reset_all():
    """清空 OCR 区全部状态（上传控件 + 校对卡片 + 降级表单）。"""
    clear_draft(_PREFIX)
    clear_manual_form(f"{_PREFIX}_mf")
    for k in list(st.session_state.keys()):
        if k.startswith(f"{_PREFIX}_"):
            del st.session_state[k]
