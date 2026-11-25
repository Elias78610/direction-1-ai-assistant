# -*- coding: utf-8 -*-
"""
用户气泡颜色配置
================
侧边栏 bottom panel 里的 st.color_picker 负责选择颜色；
选中的颜色写入 st.session_state["chat_bubble_color"]，
再由 inject_bubble_color() 动态注入 CSS。

注意：
  - 只覆盖 st.chat_message("user") 的气泡背景，AI 气泡不受影响；
  - 颜色过浅时自动把气泡文字切成深灰，保证可读性；
  - 字体颜色用 html body 提高优先级，确保能覆盖 style.py 里的默认样式。
"""

import re

import streamlit as st

DEFAULT_BUBBLE_COLOR = "#4A7BE8"
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def render_color_picker() -> str:
    """在侧边栏渲染颜色选择器，返回当前颜色（状态存 session_state）。"""
    st.session_state.setdefault("chat_bubble_color", DEFAULT_BUBBLE_COLOR)
    color = st.color_picker(
        "用户气泡颜色",
        key="chat_bubble_color",
        help="只影响你的气泡，AI 气泡保持浅灰",
    )
    st.caption("仅影响你的气泡，AI 气泡保持浅灰/白色。")
    return color


def _text_color_for(hex_color: str) -> str:
    """根据背景亮度选白字或深灰字。"""
    raw = hex_color.lstrip("#")
    try:
        r, g, b = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    except ValueError:
        return "#FFFFFF"
    # 感知亮度（0~255）
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#1F2937" if luminance > 158 else "#FFFFFF"


def inject_bubble_color(color: str = None) -> None:
    """动态注入用户气泡 CSS（不触碰 AI 气泡）。"""
    color = color or st.session_state.get("chat_bubble_color", DEFAULT_BUBBLE_COLOR)
    if not isinstance(color, str) or not _HEX_RE.match(color):
        color = DEFAULT_BUBBLE_COLOR
    text_color = _text_color_for(color)

    css = f"""
    <style>
    /* 只命中用户消息：:has(user avatar) */
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {{
        background: {color} !important;
    }}
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] p,
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] li,
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] span,
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] small,
    html body [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] [data-testid="stCaptionContainer"] p {{
        color: {text_color} !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
