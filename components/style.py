# -*- coding: utf-8 -*-
"""
全局样式（极简对话风）
========================
定位：参考 ChatGPT / Claude 的干净界面 —— 纯浅灰底、无卡片边框、
聊天气泡圆润、主色 #4A7BE8 只用于强调。

设计要点：
  - 背景 #F9FAFB，正文深灰 #1F2937，次要文字中灰 #8A93A6；
  - 主区域最大宽度 800px 居中，两侧留白；
  - 用户气泡靠右（蓝底白字），AI 气泡靠左（浅灰底深色字），隐藏默认头像；
  - 侧边栏只保留品牌、预算进度、历史会话与底部高级设置。
"""

import streamlit as st

_CSS = """
<style>
/* ══ 全局字体与背景 ══ */
html, body, [class*="css"], .stApp {
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI",
               "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: #F9FAFB; color: #1F2937; }

/* 隐藏 Streamlit 自带的菜单 / 部署按钮 / 页脚，保持沉浸感 */
#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"], footer {
  display: none !important;
}
header[data-testid="stHeader"] { background: transparent !important; }

/* ══ 主区域：800px 居中，留白充足 ══ */
[data-testid="stMainBlockContainer"] {
  max-width: 800px;
  margin: 0 auto;
  padding: 2.2rem 1.2rem 10.5rem 1.2rem;
}

/* ══ 侧边栏 ══ */
[data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid #EFF1F5;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.5rem; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 0 1rem 1rem 1rem; }

.sb-brand {
  font-size: 1.2rem; font-weight: 700; color: #111827;
  letter-spacing: .2px; display: flex; align-items: center; gap: .45rem;
}
.sb-tagline { font-size: .78rem; color: #9CA3AF; margin: .15rem 0 1.15rem 0; }
.sb-label {
  font-size: .72rem; letter-spacing: .09em; color: #A0A7B4;
  text-transform: uppercase; margin: 1.25rem 0 .55rem 0;
}
.sb-budget-meta { font-size: .8rem; color: #6B7280; margin-top: .4rem; }
.sb-divider { height: 1px; background: #F0F2F6; margin: 1.1rem 0 .2rem 0; }

/* 模式切换 radio：两个浅色胶囊 */
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] { gap: .4rem; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  background: #F4F6FA; border-radius: 10px; padding: .28rem .5rem; margin: 0;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  background: #EAF1FE;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label p {
  font-size: .82rem !important; color: #4B5563 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
  color: #2C5BB8 !important; font-weight: 600 !important;
}

/* 预算模拟 slider / 颜色选择器标签 */
[data-testid="stSidebar"] [data-testid="stSlider"] { margin-top: .15rem; }
[data-testid="stSidebar"] [data-testid="stSlider"] label p {
  font-size: .8rem !important; color: #6B7280 !important;
}
[data-testid="stSidebar"] [data-testid="stColorPicker"] label p {
  font-size: .8rem !important; color: #6B7280 !important;
}

/* 侧边栏按钮：默认无边框文字行 */
[data-testid="stSidebar"] .stButton > button {
  width: 100%;
  border: none !important;
  background: transparent !important;
  color: #4B5563 !important;
  border-radius: 10px !important;
  padding: .42rem .6rem !important;
  font-size: .88rem !important;
  font-weight: 400 !important;
  justify-content: flex-start !important;
  text-align: left !important;
  box-shadow: none !important;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: #F3F5F9 !important; color: #111827 !important;
}
/* 主按钮（新对话）：蓝色胶囊 */
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[type="primary"] {
  background: #4A7BE8 !important; color: #FFFFFF !important;
  font-weight: 500 !important; justify-content: center !important;
  text-align: center !important; padding: .55rem .6rem !important;
  border-radius: 12px !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
[data-testid="stSidebar"] .stButton > button[type="primary"]:hover {
  background: #3F6DD6 !important; color: #FFFFFF !important;
}

/* 原生进度条：细、圆角、蓝色 */
[data-testid="stProgress"] { margin-top: .2rem; }
[data-testid="stProgress"] > div {
  background: #EEF1F6 !important; border-radius: 999px !important; height: 6px !important;
}
[data-testid="stProgress"] div[role="progressbar"] {
  background: #4A7BE8 !important; border-radius: 999px !important;
}

/* 侧边栏底部面板：高级设置 + 用户气泡颜色，用 flex 压到底部 */
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
  min-height: calc(100vh - 150px);
}
[data-testid="stSidebar"] [class*="st-key-sidebar_bottom_panel"] {
  margin-top: auto !important;
}
[data-testid="stSidebar"] [class*="st-key-sidebar_bottom_panel"] [data-testid="stColorPicker"] {
  margin-top: .45rem;
}
[data-testid="stExpander"] {
  border: 1px solid #EEF0F4 !important;
  border-radius: 12px !important;
  background: #FCFCFD !important;
  box-shadow: none !important;
}
[data-testid="stExpander"] summary { font-size: .85rem !important; color: #6B7280 !important; }

/* ══ 空状态 ══ */
.empty-state { text-align: center; padding: 11vh 0 1.4rem 0; }
.empty-mark { font-size: 2rem; margin-bottom: .85rem; }
.empty-title { font-size: 1.55rem; font-weight: 650; color: #111827; letter-spacing: -.01em; }
.empty-sub { font-size: .95rem; color: #8A93A6; margin-top: .6rem; }
.quick-label {
  text-align: center; font-size: .76rem; color: #B0B7C3;
  letter-spacing: .09em; text-transform: uppercase; margin: .4rem 0 .9rem 0;
}

/* ══ 快捷提示词按钮：胶囊形 ══ */
[data-testid="stMainBlockContainer"] .stButton > button {
  background: #FFFFFF !important;
  border: 1px solid #E9EDF3 !important;
  border-radius: 999px !important;
  color: #4B5563 !important;
  font-size: .87rem !important;
  font-weight: 400 !important;
  padding: .58rem .95rem !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, .02) !important;
  justify-content: flex-start !important;
  text-align: left !important;
}
[data-testid="stMainBlockContainer"] .stButton > button:hover {
  border-color: #C9D8F7 !important;
  color: #2C5BB8 !important;
  background: #F8FAFF !important;
}

/* ══ 聊天气泡 ══ */
[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0 !important;
  margin: .15rem 0 .9rem 0 !important;
  display: flex !important;
  align-items: flex-start;
  gap: 0 !important;
}
/* 隐藏默认头像，保留纯气泡 */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] { display: none !important; }

[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
  flex: 0 0 auto !important;
  box-sizing: border-box !important;
  /* 注意：Streamlit 1.41 会给内部 Markdown 写死行内宽度，
     用 fit-content 会把气泡压成最小宽度；AI 气泡改用固定宽度（68% 上限） */
  width: 68% !important;
  max-width: 68% !important;
  margin: 0 !important;
  padding: .8rem 1.05rem !important;
  background: #F1F3F7 !important;
  border: none !important;
  border-radius: 4px 18px 18px 18px !important;
  color: #1F2937 !important;
  line-height: 1.72 !important;
  font-size: .95rem !important;
  box-shadow: none !important;
}

/* 用户消息：整行反向 → 气泡靠右；蓝底白字，右上角收口 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  flex-direction: row-reverse;
  justify-content: flex-start;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
  /* 用户输入是短句，贴合文字宽度即可 */
  flex: 0 1 auto !important;
  width: fit-content !important;
  max-width: 78% !important;
  background: #4A7BE8 !important;
  border-radius: 18px 4px 18px 18px !important;
  color: #FFFFFF !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] li,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] span {
  color: #FFFFFF !important;
}

/* 气泡内文字间距收紧 */
[data-testid="stChatMessageContent"] p { margin: 0 0 .35rem 0 !important; }
[data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0 !important; }
[data-testid="stChatMessageContent"] ul,
[data-testid="stChatMessageContent"] ol { margin: .2rem 0 .35rem 0; padding-left: 1.1rem; }
[data-testid="stChatMessageContent"] blockquote {
  border-left: 2px solid #DDE3EE; margin: .4rem 0 0 0; padding: .1rem 0 .1rem .7rem;
  color: #6B7280;
}

/* 附件消息：图片圆角、语音条宽度、用户气泡里的说明文字保持白色 */
[data-testid="stChatMessageContent"] img { border-radius: 12px; }
[data-testid="stChatMessageContent"] audio { width: 100%; height: 42px; border-radius: 10px; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]:has(audio) {
  width: 300px !important;
}
/* 小票缩略图：固定气泡宽度，避免被 fit-content 压成小图 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]:has(img) {
  width: 260px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] small,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] [data-testid="stCaptionContainer"] *,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] [data-testid="stMarkdownContainer"] * {
  color: rgba(255, 255, 255, .9) !important;
}

/* ══ 多模态上传入口（固定在输入框正上方）══ */
[data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
  position: fixed;
  bottom: 96px;
  left: calc(50% + 168px);   /* 侧边栏宽 336px 时与主区域中心对齐 */
  transform: translateX(-50%);
  width: min(800px, calc(100vw - 336px - 2rem));
  z-index: 1000;
  background: #F9FAFB;
  padding: .25rem 19px .5rem 19px;
  box-sizing: border-box;
}
#chat-bottom-anchor { height: 0; scroll-margin-bottom: 170px; }

[data-testid="stPopover"] > button {
  background: #FFFFFF !important;
  border: 1px solid #E9EDF3 !important;
  border-radius: 999px !important;
  color: #4B5563 !important;
  font-size: .84rem !important;
  font-weight: 400 !important;
  padding: .42rem .9rem !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, .02) !important;
}
[data-testid="stPopover"] > button:hover {
  border-color: #C9D8F7 !important;
  color: #2C5BB8 !important;
  background: #F8FAFF !important;
}
[data-testid="stPopoverBody"] { min-width: 320px; }
[data-testid="stPopover"] [data-testid="stFileUploader"] { font-size: .85rem; }

/* 思考中的灰字 */
.thinking { color: #9CA3AF; font-size: .84rem; }

/* ══ 底部输入框：居中、悬浮、圆角 ══ */
[data-testid="stBottomBlockContainer"] {
  max-width: 800px;
  margin: 0 auto;
  padding: .5rem 1.2rem 1.15rem 1.2rem;
  background: #F9FAFB;
}
[data-testid="stChatInput"] {
  background: #FFFFFF !important;
  border: 1px solid #E6E9F0 !important;
  border-radius: 18px !important;
  box-shadow: 0 8px 24px rgba(17, 24, 39, .05) !important;
  padding: .15rem .2rem !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: #C6D7F8 !important;
  box-shadow: 0 8px 24px rgba(74, 123, 232, .10) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important;
  color: #1F2937 !important;
  font-size: .95rem !important;
}
[data-testid="stChatInputTextArea"]::placeholder { color: #B0B7C3 !important; }
[data-testid="stChatInputSubmitButton"] {
  background: #4A7BE8 !important;
  color: #FFFFFF !important;
  border-radius: 12px !important;
}
[data-testid="stChatInputSubmitButton"]:hover { background: #3F6DD6 !important; }

/* ══ 确认卡片（st.container(border=True)）══ */
[class*="st-key-draft_card"] {
  background: #FFFFFF !important;
  border: 1px solid #E9EDF3 !important;
  border-radius: 16px !important;
  padding: .2rem .15rem .1rem .15rem;
  box-shadow: 0 8px 24px rgba(17, 24, 39, .04);
}
.draft-title {
  font-size: .98rem; font-weight: 650; color: #111827; margin: .15rem 0 .45rem 0;
}
[class*="st-key-draft_card"] .stButton > button {
  height: 40px !important;
  min-height: 40px !important;
  padding: 0 1rem !important;
  border-radius: 10px !important;
  border: 1px solid #E9EDF3 !important;
  background: #FFFFFF !important;
  color: #4B5563 !important;
  font-size: .88rem !important;
  font-weight: 500 !important;
  justify-content: center !important;
  text-align: center !important;
  box-shadow: none !important;
}
[class*="st-key-draft_card"] .stButton > button:hover {
  border-color: #C9D8F7 !important;
  color: #2C5BB8 !important;
  background: #F8FAFF !important;
}
[class*="st-key-draft_card"] .stButton > button[kind="primary"],
[class*="st-key-draft_card"] .stButton > button[type="primary"] {
  background: #4A7BE8 !important;
  border-color: #4A7BE8 !important;
  color: #FFFFFF !important;
}
[class*="st-key-draft_card"] .stButton > button[kind="primary"]:hover,
[class*="st-key-draft_card"] .stButton > button[type="primary"]:hover {
  background: #3F6DD6 !important;
  border-color: #3F6DD6 !important;
}

/* 输入框下方的提示语 */
[data-testid="stChatInput"] + div { display: none; }
</style>
"""


def apply_global_css() -> None:
    """注入全局样式（app.py 启动时调用一次）。"""
    st.markdown(_CSS, unsafe_allow_html=True)


# ── 旧版页面组件兼容函数（新的对话界面不再使用；保留是为了不破坏 sections/ 里的旧代码）──
def page_header(title: str, subtitle: str = "") -> None:
    """兼容旧版主区域标题。"""
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def section_header(icon: str, title: str, desc: str = "") -> None:
    """兼容旧版分区标题。"""
    st.markdown(f"#### {icon} {title}")
    if desc:
        st.caption(desc)
