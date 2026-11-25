# -*- coding: utf-8 -*-
"""
自然语言记账（聊天）Section · sections/nl_bookkeeping.py
==========================================================
职责：
  1. 对话式记账：顶部用法提示 + 气泡对话（st.chat_message）+ 底部输入框（st.chat_input）；
  2. 对话历史保存在 st.session_state，页面重跑（st.rerun）不会丢失；
  3. 演示模式（st.session_state["demo_mode"] 为 True）：本地规则生成模拟回复，
     不请求后端，适合答辩演示；
  4. 真实模式：POST {后端地址}/chat，请求体 {"message": "..."}，
     所有异常统一转换成友好的中文提示。

约定：
  - 本文件只对外提供 render()；页面配置（st.set_page_config）、侧边栏导航、
    全局样式都由 app.py / components 统一负责，这里不再重复设置；
  - 不新增第三方依赖：仅用 Streamlit 原生组件 + 项目已安装的 requests。

后端接口约定（与 FastAPI 对齐时确认）：
  POST /chat   Content-Type: application/json
  Request : {"message": "今天吃饭花了 35 块"}
  Response: {"reply": "已记一笔：餐饮 35.00 元"}
            同时兼容 {"answer": ...} / {"message": ...} / 纯文本等返回形式。
"""

import json
import os
import re

import requests
import streamlit as st

# ── 模块级常量 ────────────────────────────────────────────────
_HISTORY_KEY = "nl_bookkeeping_history"      # 对话历史在 session_state 中的键
_DEFAULT_BASE_URL = "http://127.0.0.1:8000"  # 后端默认地址（可在左侧「高级设置」覆盖）
_CHAT_PATH = "/chat"                          # 聊天接口路径
_TIMEOUT = 60                                 # 请求超时（秒），聊天接口会调大模型，与项目 LLM 超时一致

# 首次进入页面的欢迎语（同时作为空历史的占位内容）
_WELCOME = (
    "你好，我是记账助手 💰\n\n"
    "直接用一句话记账即可，例如：**今天吃饭花了 35 块**、**昨天打车 28 元**。\n\n"
    "演示模式下我会在本地模拟回复，不会请求后端。"
)

# 用户气泡靠右、AI 气泡靠左：Streamlit 默认全部左对齐，
# 这里用 :has() 选中「用户头像」所在的消息行并反向排列；样式只作用于聊天气泡，
# 不会影响仪表盘等其他页面。兼容不同 Streamlit 版本的两套头像 testid。
_CSS = """
<style>
/* ── 消息行：去掉默认的整行灰底，保留少量上下间距 ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 2px 4px !important;
    margin-bottom: 4px;
    align-items: flex-start;
}

/* ── 气泡本体：宽度贴合文字（不铺满整行），最长 72%，圆角 + 内边距 ── */
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
    flex: 0 1 auto !important;
    width: fit-content !important;
    max-width: 72% !important;
    margin: 0 !important;
    padding: 10px 14px !important;
    background: #F6F8FB !important;
    border: 1px solid #E5EAF3 !important;
    border-radius: 4px 14px 14px 14px !important;
}

/* ── 用户消息：整行反向排列 → 头像贴右、气泡随之靠右 ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    flex-direction: row-reverse;
    justify-content: flex-start;
}

/* ── 用户气泡：柔和蓝底白字，右上角收一个小圆角 ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"],
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
    background: #4A7BE8 !important;
    border-color: #4A7BE8 !important;
    border-radius: 14px 4px 14px 14px !important;
}

/* ── 用户气泡内文字保持白色（覆盖全局 Markdown 深色文字）── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] li,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] span,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] li,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] span {
    color: #FFFFFF !important;
}
</style>
"""

# ── 演示模式的本地规则（不做网络请求）────────────────────────
_INCOME_WORDS = ("工资", "收入", "红包", "奖金", "报销", "进账", "退款")
_QUERY_WORDS = ("多少", "查", "统计", "汇总", "一共", "总共", "对比")

# 分类关键词：命中即归入对应分类，未命中记「其他」
_CATEGORY_RULES = (
    ("餐饮", ("吃", "饭", "餐", "外卖", "咖啡", "奶茶", "火锅", "早餐", "午饭", "晚饭", "零食")),
    ("交通", ("打车", "地铁", "公交", "加油", "停车", "高铁", "机票", "滴滴")),
    ("购物", ("买", "淘宝", "京东", "拼多多", "超市", "衣服", "鞋", "数码")),
    ("娱乐", ("电影", "游戏", "唱歌", "ktv", "演出", "旅游")),
    ("居住", ("房租", "水电", "燃气", "物业", "宽带")),
    ("医疗", ("药", "医院", "看病", "体检")),
    ("教育", ("书", "课程", "学费", "培训")),
)

# 金额：优先匹配带「块/元」的数字，避免把日期、人数误当金额
_AMOUNT_WITH_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:块钱|块|元)")
_AMOUNT_ANY = re.compile(r"(\d+(?:\.\d+)?)")


class _ChatError(Exception):
    """聊天请求失败时携带的友好中文提示。"""


def _is_demo_mode() -> bool:
    """演示模式判断。

    优先读取侧边栏「高级设置」写入的 st.session_state["demo_mode"]；
    会话里尚未初始化时，兼容环境变量 LEDGER_DEMO_MODE（与项目 config.py 约定一致）。
    """
    value = st.session_state.get("demo_mode")
    if value is not None:
        return bool(value)
    return os.environ.get("LEDGER_DEMO_MODE", "0") in ("1", "true", "True", "yes", "on")


def _api_base_url() -> str:
    """后端地址：优先用会话里的运行时配置（左侧「高级设置」可改），否则用默认值。"""
    base = st.session_state.get("api_base_url") or _DEFAULT_BASE_URL
    return str(base).rstrip("/")


def _extract_amount(text: str):
    """从一句话里提取金额：优先带「块/元」的数字，否则取最后一个数字；没找到返回 None。"""
    matches = _AMOUNT_WITH_UNIT.findall(text)
    if not matches:
        matches = _AMOUNT_ANY.findall(text)
    return float(matches[-1]) if matches else None


def _guess_category(text: str) -> str:
    """按关键词粗略猜分类（仅演示模式使用）。"""
    lower = text.lower()
    for category, words in _CATEGORY_RULES:
        if any(word in lower for word in words):
            return category
    return "其他"


def _demo_reply(text: str) -> str:
    """演示模式回复：纯本地规则模拟记账结果，不发送任何网络请求。"""
    amount = _extract_amount(text)

    # 1) 识别到金额 → 模拟记一笔
    if amount is not None:
        is_income = any(word in text for word in _INCOME_WORDS)
        kind = "收入" if is_income else "支出"
        category = "收入" if is_income else _guess_category(text)
        return (
            f"收到，已为你记一笔{kind}：\n\n"
            f"- 分类：**{category}**\n"
            f"- 金额：**¥{amount:,.2f}**\n"
            f"- 原始语句：{text}\n\n"
            "> 演示模式：以上为本地模拟结果，未写入真实账本；"
            "关闭「演示模式」并启动后端后，会调用 FastAPI 真实入库。"
        )

    # 2) 像在查账 → 用内置示例数据回答（数字与演示数据保持一致）
    if any(word in text for word in _QUERY_WORDS):
        return (
            "（演示数据）本月共有 **11 笔**支出，合计 **¥1,752.00**；"
            "收入 **¥8,000.00**，结余 **¥6,248.00**。\n\n"
            "> 演示模式下展示的是内置示例数据，不是实时统计。"
        )

    # 3) 其他情况 → 引导用户补充金额
    return (
        "我没识别到金额呢～可以这样说：\n\n"
        "· 今天吃饭花了 35 块\n"
        "· 昨天打车 28 元\n"
        "· 发工资 8000 元"
    )


def _request_reply(message: str) -> str:
    """真实模式：POST /chat，返回 AI 回复文本；失败抛 _ChatError（中文提示）。"""
    url = f"{_api_base_url()}{_CHAT_PATH}"

    try:
        resp = requests.post(url, json={"message": message}, timeout=_TIMEOUT)
    except requests.exceptions.Timeout:
        raise _ChatError(
            f"请求超时（{_TIMEOUT}s）：后端响应较慢，请稍后重试；演示时可先在左侧勾选「演示模式」。")
    except requests.exceptions.ConnectionError:
        raise _ChatError(
            f"无法连接后端服务（{url}）：请确认 FastAPI 已启动，"
            "或在左侧「高级设置」勾选「演示模式」。")
    except requests.exceptions.RequestException as exc:
        raise _ChatError(f"请求发送失败：{exc}")

    if resp.status_code >= 400:
        raise _ChatError(f"后端返回错误（HTTP {resp.status_code}）：{resp.text[:160]}")

    try:
        data = resp.json()
    except ValueError:
        # 后端直接返回纯文本时也兼容
        text = (resp.text or "").strip()
        if text:
            return text
        raise _ChatError("后端返回内容为空，请检查 /chat 接口实现。")

    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        # 兼容多种字段命名，取第一个非空字符串
        for key in ("reply", "answer", "message", "content", "response", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        # 兜底：结构化返回原样展示，便于排查接口字段
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


def _init_history() -> None:
    """初始化对话历史（首次进入页面时写入欢迎语）。"""
    if _HISTORY_KEY not in st.session_state:
        st.session_state[_HISTORY_KEY] = [{"role": "assistant", "content": _WELCOME}]


def render():
    """页面渲染入口：app.py 选中「自然语言记账（聊天）」导航时调用。"""
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── 1. 顶部标题 + 用法提示 + 当前模式 ──
    st.markdown(
        '<div class="ledger-section-title"><span>💬</span>自然语言记账（聊天）</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="ledger-section-desc">像聊天一样记账：说清楚「花了多少、花在哪」，'
        'AI 自动识别金额与分类。</div>',
        unsafe_allow_html=True)

    demo = _is_demo_mode()
    if demo:
        st.markdown(
            '<div class="ledger-banner ledger-banner-info">'
            '<span class="b-strong">当前为演示模式</span>'
            '　聊天回复由本地规则模拟生成，不请求后端；'
            '关闭左侧「高级设置」中的演示模式即可连接真实 FastAPI。</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="ledger-banner ledger-banner-normal">'
            '<span class="b-strong">真实模式</span>'
            f'　消息将发送到 {_api_base_url()}{_CHAT_PATH}；'
            '后端未启动时请到左侧「高级设置」勾选「演示模式」。</div>',
            unsafe_allow_html=True)

    st.caption("示例：今天吃饭花了 35 块 ｜ 昨天打车 28 元 ｜ 发工资 8000 元")

    # ── 2. 历史消息：逐条渲染气泡（AI 靠左 / 用户靠右，由上面的 CSS 控制对齐）──
    _init_history()
    for message in st.session_state[_HISTORY_KEY]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ── 3. 输入框：st.chat_input 原生支持回车发送 ──
    prompt = st.chat_input("输入一句话记账，例如：今天吃饭花了 35 块")
    if prompt and prompt.strip():
        user_text = prompt.strip()
        st.session_state[_HISTORY_KEY].append({"role": "user", "content": user_text})

        # 演示模式：本地模拟，不请求后端；真实模式：调用后端 /chat
        if demo:
            reply = _demo_reply(user_text)
        else:
            with st.spinner("AI 正在记账…"):
                try:
                    reply = _request_reply(user_text)
                except _ChatError as exc:
                    reply = f"⚠️ {exc}"
                except Exception as exc:  # 兜底：任何意外异常都转成友好提示，不让页面崩
                    reply = f"⚠️ 聊天请求出现异常：{exc}"

        st.session_state[_HISTORY_KEY].append({"role": "assistant", "content": reply})
        # 立即重跑：把本轮「用户消息 + AI 回复」渲染到页面上
        st.rerun()