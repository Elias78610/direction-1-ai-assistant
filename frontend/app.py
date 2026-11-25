# -*- coding: utf-8 -*-
"""
记账 AI 助手 · 前端交互闭环（Mock 版）
========================================
本轮重点：
  1. 可编辑确认卡片：st.container(border=True) + 金额/分类/日期/备注，
     AA 自动折算人均；确认后才写入「已成功记录」只读气泡；
  2. 思考中 spinner（2 秒）、空状态 3 个快捷按钮、手动记账降级表单；
  3. Mock 统计图表（分类饼图 + 月度柱状图，透明背景 + 主色蓝）；
  4. 高级设置里的预算使用率滑块：>1.0 时聊天区顶部红色超支警告，
     联动右下角情绪小球；
  5. 前端模拟「上传小票」：插入占位小票图 → 识别中 → 确认卡片 → 才入库。

所有涉及后端计算的位置都用 `# TODO: 接入后端接口` 标出；
当前所有金额/分类/日期/图表/预算均为前端写死的 Mock 数据。
"""

import calendar
import datetime
import logging
import re
import sys
import time
import uuid
from io import BytesIO
from pathlib import Path

# 兼容两种启动方式：
#   1) 在 frontend/ 目录内：streamlit run app.py
#   2) 在仓库根目录：streamlit run frontend/app.py
_FRONTEND_ROOT = Path(__file__).resolve().parent
if str(_FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_FRONTEND_ROOT))

import streamlit as st
import streamlit.components.v1 as components

import config
from components import calendar_view, custom_style, emotion_mascot
from components import sidebar as sidebar_ui
from components import stats_view
from components.style import apply_global_css
from services import api_client
from utils import current_month_key, month_range, to_error_message

logger = logging.getLogger(__name__)

# ── 页面全局设置（必须是第一条 Streamlit 命令）──
st.set_page_config(
    page_title="记账 AI 助手",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_css()

# ── Mock 数据与常量 ────────────────────────────────────────────
DEMO_BUDGET = {"budget": 2061.17}
CATEGORIES = ("餐饮", "交通", "购物", "娱乐", "居住", "医疗", "其他")
SOURCE_LABELS = {
    "text": "文本记账",
    "nlp": "自然语言记账",
    "receipt": "小票识别",
    "ocr": "小票识别",
    "voice": "语音识别",
    "manual": "手动录入",
}

# 空状态：只保留 3 个快捷输入按钮
QUICK_PROMPTS = (
    "帮我记一笔餐饮消费100元",
    "3个人吃火锅300 AA",
    "查一下本月预算",
)

# Mock NLU 的关键词规则（后续由后端 /api/v1/expenses/parse 替代）
_INCOME_WORDS = ("工资", "收入", "红包", "奖金", "退款")
_CATEGORY_RULES = (
    ("餐饮", ("吃", "饭", "餐", "咖啡", "奶茶", "外卖", "火锅")),
    ("交通", ("打车", "地铁", "公交", "滴滴", "加油")),
    ("购物", ("买", "淘宝", "京东", "超市", "衣服", "鞋")),
    ("娱乐", ("电影", "游戏", "唱歌", "旅游")),
    ("居住", ("房租", "水电", "物业", "宽带")),
    ("医疗", ("药", "医院", "体检", "看病")),
)
_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_AMOUNT_WITH_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:块钱|块|元)")
_AMOUNT_ANY = re.compile(r"(\d+(?:\.\d+)?)")
_PEOPLE_ARABIC = re.compile(r"(\d+)\s*个?\s*人")
_PEOPLE_CHINESE = re.compile(r"([一二两三四五六七八九十])\s*个?\s*人")


# ═══════════════════════════════════════════════════════════════
# Demo / 真实接口分支与数据加载
# ═══════════════════════════════════════════════════════════════

def _is_demo_mode() -> bool:
    """侧边栏「演示模式」开关：True 走本地 Mock，False 走 api_client。"""
    return bool(st.session_state.get("demo_mode", True))


def _error_text(exc) -> str:
    """统一把接口异常转成页面友好文案。"""
    return to_error_message(exc)


def _flush_api_error() -> None:
    """显示并清空本轮接口错误（每个 rerun 只提示一次）。"""
    message = st.session_state.pop("_api_error", None)
    if message:
        st.error(f"⚠️ {message}")


def _load_categories() -> list:
    """类别：Demo 用内置 7 类；真实模式加载 /api/v1/categories（缓存）。"""
    if _is_demo_mode():
        return list(CATEGORIES)
    cached = st.session_state.get("categories_real")
    if cached:
        return list(cached)
    try:
        data = api_client.fetch_categories()
        categories = [str(item) for item in data if str(item).strip()] \
            if isinstance(data, list) else []
        if categories:
            st.session_state["categories_real"] = categories
            return categories
        st.session_state["_api_error"] = "类别接口返回为空，已暂用内置类别。"
    except Exception as exc:
        st.session_state["_api_error"] = _error_text(exc)
    return list(CATEGORIES)


def _categories() -> list:
    """当前渲染使用的类别列表（真实模式加载失败时回退内置类别）。"""
    if _is_demo_mode():
        return list(CATEGORIES)
    return list(st.session_state.get("categories_real") or CATEGORIES)


def _budget_snapshot() -> dict:
    """预算：Demo 用滑块模拟；真实模式 GET /api/v1/budgets/{month}。"""
    month = current_month_key()
    if _is_demo_mode():
        ratio = float(st.session_state.get("budget_ratio_pct", 85)) / 100
        budget = float(DEMO_BUDGET["budget"])
        spent = round(budget * ratio)
        return {"month": month, "amount": budget, "spent": spent,
                "ratio": ratio, "usage_percent": ratio * 100,
                "missing": False}
    try:
        data = api_client.fetch_budgets(month) or {}
        amount = float(data.get("amount") or 0)
        spent = float(data.get("spent") or 0)
        usage = data.get("usage_percent")
        ratio = (float(usage) / 100) if usage is not None else (spent / amount if amount else 0)
        usage_percent = float(usage) if usage is not None else ratio * 100
        return {"month": month, "amount": amount, "spent": spent,
                "ratio": ratio, "usage_percent": usage_percent,
                "missing": amount <= 0, "raw": data}
    except api_client.ApiError as exc:
        if exc.status_code == 404:
            return {"month": month, "amount": 0.0, "spent": 0.0, "ratio": 0.0,
                    "usage_percent": 0.0, "missing": True}
        st.session_state["_api_error"] = _error_text(exc)
    except Exception as exc:
        st.session_state["_api_error"] = _error_text(exc)
    return {"month": month, "amount": 0.0, "spent": 0.0, "ratio": 0.0,
            "usage_percent": 0.0, "missing": True}


def _contract_source(source) -> str:
    """页面来源 → 契约 source：manual / nlp / ocr。"""
    mapping = {"text": "nlp", "nlp": "nlp", "receipt": "ocr",
               "ocr": "ocr", "manual": "manual", "voice": "nlp"}
    return mapping.get(str(source or "text").lower(), "manual")


def _create_expense(amount, category, date_str, note, source, draft=None) -> None:
    """真实模式新增账目（字段与后端 ExpenseCreate 一致）。"""
    if _is_demo_mode():
        return
    if draft and draft.get("direction") == "income":
        raise api_client.ApiError(400, "接口契约 v1 仅支持支出记账，收入暂未开放。")
    contract_source = _contract_source(source)
    payload = {
        "amount": f"{float(amount):.2f}",
        "category": str(category),
        "spent_at": f"{date_str}T00:00:00",
        "note": note or None,
        "source": contract_source,
        "raw_text": (draft or {}).get("raw_input") or None,
    }
    # 后端 ExpenseCreate 当前没有 image_path 字段；OCR 图片仍保留在聊天记录中，
    # 等后端 Schema 补充后再随创建请求发送。
    if contract_source == "nlp" and not payload["raw_text"]:
        payload["raw_text"] = note or "自然语言记账"
    api_client.create_transaction(payload)


def _load_month_expenses(year: int, month: int) -> list:
    """真实模式：读取指定月份账目列表。"""
    start = datetime.date(year, month, 1).isoformat()
    last_day = calendar.monthrange(year, month)[1]
    end = datetime.date(year, month, last_day).isoformat()
    data = api_client.fetch_transactions(start_date=start, end_date=end,
                                         limit=500, offset=0)
    return list((data or {}).get("items") or [])


def _month_bounds(month_key: str) -> tuple:
    """YYYY-MM → (start_date, end_date) 字符串。"""
    first, last = month_range(month_key)
    return first.isoformat(), last.isoformat()


# ═══════════════════════════════════════════════════════════════
# 会话状态
# ═══════════════════════════════════════════════════════════════

def _clear_pending() -> None:
    """清理当前会话里的临时交互状态。"""
    for key in ("pending_draft", "pending_prompt", "pending_upload", "pending_receipt"):
        st.session_state.pop(key, None)


def _new_chat() -> None:
    """新建空会话并设为当前会话。"""
    session = {"id": uuid.uuid4().hex[:8], "title": "新对话", "messages": []}
    st.session_state.sessions.append(session)
    st.session_state.current_session = session["id"]
    st.session_state.messages = session["messages"]
    _clear_pending()


def _init_state() -> None:
    """初始化会话状态；兼容旧版 view_mode 文案。"""
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("sessions", [])
    st.session_state.setdefault("current_session", None)
    st.session_state.setdefault("upload_round", 0)
    st.session_state.setdefault("demo_mode", True)
    st.session_state.setdefault("api_base_url", config.API_BASE_URL)
    st.session_state.setdefault("budget_ratio_pct", 85)
    st.session_state.setdefault("budget_ratio", 0.85)
    st.session_state.setdefault("chat_bubble_color", "#4A7BE8")
    st.session_state.setdefault("selected_date", "2026-11-05")
    st.session_state.setdefault("view_mode", "💬 对话")

    # 兼容上一版的双模式文案，避免 radio 因 session_state 值不在 options 中报错
    mode = st.session_state.get("view_mode")
    if mode == "💬 对话模式":
        st.session_state["view_mode"] = "💬 对话"
    elif mode == "📅 日历模式":
        st.session_state["view_mode"] = "📅 日历"
    elif mode not in ("💬 对话", "📅 日历", "📊 统计"):
        st.session_state["view_mode"] = "💬 对话"

    if not st.session_state.sessions:
        _new_chat()


def _current_session() -> dict | None:
    for session in st.session_state.sessions:
        if session["id"] == st.session_state.current_session:
            return session
    return None


def _switch_chat(session_id: str) -> None:
    for session in st.session_state.sessions:
        if session["id"] == session_id:
            st.session_state.current_session = session_id
            st.session_state.messages = session["messages"]
            _clear_pending()
            return


def _rename_current(title_seed: str) -> None:
    title = (title_seed or "").strip().replace("\n", " ")
    title = title[:14] + ("…" if len(title) > 14 else "")
    session = _current_session()
    if session is None:
        return
    if session.get("title") == "新对话":
        session["title"] = title or "新对话"


# ═══════════════════════════════════════════════════════════════
# Mock NLU（后续替换为 /api/v1/expenses/parse）
# ═══════════════════════════════════════════════════════════════

def _extract_amount(text: str):
    matches = _AMOUNT_WITH_UNIT.findall(text)
    if not matches:
        matches = _AMOUNT_ANY.findall(text)
    return float(matches[-1]) if matches else None


def _extract_people(text: str):
    match = _PEOPLE_ARABIC.search(text)
    if match:
        return int(match.group(1))
    match = _PEOPLE_CHINESE.search(text)
    if match:
        return _CN_NUM.get(match.group(1))
    return None


def _guess_category(text: str) -> str:
    lower = text.lower()
    for category, words in _CATEGORY_RULES:
        if any(word in lower for word in words):
            return category
    return "其他"


def _build_draft(amount, category, note, source, header,
                 direction="expense", is_aa=False,
                 aa_total=None, aa_people=None, aa_per=None, raw_input=""):
    """构造确认卡片所需的草稿（Demo 与真实解析共用）。"""
    if category not in _categories():
        category = "其他"
    return {
        "id": uuid.uuid4().hex[:8],
        "amount": round(float(amount), 2),
        "category": category,
        "date": datetime.date.today().isoformat(),
        "note": note or "",
        "direction": direction,
        "is_aa": bool(is_aa),
        "aa_total": aa_total,
        "aa_people": aa_people,
        "aa_per": aa_per,
        "source": source,
        "header": header,
        "raw_input": raw_input,
    }


def _budget_reply() -> str:
    """预算意图回复：Demo 用滑块模拟，真实模式读取 /api/v1/budgets/{month}。"""
    if not _is_demo_mode():
        try:
            row = api_client.fetch_budgets(current_month_key()) or {}
        except api_client.ApiError as exc:
            if exc.status_code == 404:
                return "📊 本月还没有设置预算。可在后端预算模块设置后，再问我一次。"
            raise
        amount = float(row.get("amount") or 0)
        spent = float(row.get("spent") or 0)
        remaining = float(row.get("remaining") or 0)
        usage = float(row.get("usage_percent") or 0)
        tail = (f"已超支 **¥{abs(remaining):,.2f}**" if remaining < 0
                else f"剩余 **¥{remaining:,.2f}**")
        return (
            "📊 **本月预算进度**\n\n"
            f"已用 **{usage:.0f}%**，已支出 **¥{spent:,.2f}** / "
            f"预算 **¥{amount:,.2f}**，{tail}。\n\n"
            f"> {row.get('message') or '数据来自 GET /api/v1/budgets/{month}。'}"
        )

    ratio_value = st.session_state.get("budget_ratio", 0.85)
    ratio = float(ratio_value) if ratio_value is not None else 0.85
    budget = float(DEMO_BUDGET["budget"])
    spent_amount: int = round(budget * ratio)  # 展示取整，默认 85% → ¥1,752
    remaining: float = budget - spent_amount
    tail = (f"已超支 **¥{abs(remaining):,.2f}**" if remaining < 0
            else f"剩余 **¥{remaining:,.2f}**")
    return (
        "📊 **本月预算进度**\n\n"
        f"已用 **{ratio * 100:.0f}%**，已支出 **¥{spent_amount:,.2f}** / "
        f"预算 **¥{budget:,.2f}**，{tail}。\n\n"
        "- 餐饮 **28.5%**\n"
        "- 购物 **17.1%**\n"
        "- 娱乐休闲 **14.8%**\n\n"
        "> 当前为演示数据。"
    )


def _analysis_reply() -> str:
    """消费分析回复：Demo 用固定文案，真实模式读取统计接口。"""
    if not _is_demo_mode():
        month = current_month_key()
        start, end = _month_bounds(month)
        summary = api_client.fetch_stats_summary(month) or {}
        category_data = api_client.fetch_stats_category(start, end) or {}
        items = category_data.get("items") or []
        total = summary.get("total_amount") or category_data.get("total_amount") or "0.00"
        count = summary.get("count") or 0
        lines = [f"📊 本月共 **{count} 笔**消费，合计 **¥{float(total):,.2f}**：", ""]
        for item in items[:5]:
            amount = float(item.get("amount") or 0)
            ratio = float(item.get("ratio") or 0) * 100
            lines.append(f"- {item.get('category') or '未分类'} **{amount:,.2f} 元**（{ratio:.1f}%）")
        if len(lines) == 2:
            lines.append("- 暂无分类数据")
        return "\n".join(lines)

    return (
        "📊 本月共 **11 笔**消费，合计 **¥1,752.00**：\n\n"
        "- 餐饮 **28.5%**\n"
        "- 购物 **17.1%**\n"
        "- 娱乐休闲 **14.8%**\n"
        "- 其他 **39.6%**\n\n"
        "餐饮接近三成，是本月最大的开销。"
    )


def mock_nlu(text: str) -> dict:
    """Mock 意图识别：AA/普通记账返回可编辑 draft，其余返回文字 reply。"""
    prompt = (text or "").strip()
    lower = prompt.lower()

    # 1) AA 平摊
    if any(keyword in prompt for keyword in ("平摊", "几个人")) or "aa" in lower:
        people = _extract_people(prompt)
        rest = _PEOPLE_ARABIC.sub(" ", prompt)
        rest = _PEOPLE_CHINESE.sub(" ", rest)
        total = _extract_amount(rest)
        if total is None and people is None:
            total = _extract_amount(prompt)
        if total is None:
            return {
                "intent": "help",
                "reply": (
                    "检测到 AA 平摊，但没看到总金额。可以这样说：\n\n"
                    "- 「3 个人吃火锅 300 AA」\n"
                    "- 「4 个人平摊 240 元」"
                ),
            }
        if not people:
            people = 2
        per = total / people
        category = _guess_category(prompt)
        draft = _build_draft(
            per, category, prompt, "text", "已解析这段描述，请确认：",
            direction="expense", is_aa=True,
            aa_total=total, aa_people=people, aa_per=per, raw_input=prompt,
        )
        return {"intent": "aa", "draft": draft}

    # 2) 预算
    if any(keyword in prompt for keyword in ("预算", "超支", "还剩多少")):
        return {"intent": "budget", "reply": _budget_reply()}

    # 3) 消费分析
    if any(keyword in prompt for keyword in ("分析", "结构", "统计", "多少")):
        return {"intent": "analysis", "reply": _analysis_reply()}

    # 4) 普通记账
    amount = _extract_amount(prompt)
    if amount is not None:
        category = _guess_category(prompt)
        direction = "income" if any(word in prompt for word in _INCOME_WORDS) else "expense"
        draft = _build_draft(
            amount, category, prompt, "text", "已解析这段描述，请确认：",
            direction=direction, raw_input=prompt,
        )
        return {"intent": "record", "draft": draft}

    # 5) 兜底引导
    return {
        "intent": "help",
        "reply": (
            "我可以帮你记账、AA 平摊、查预算、分析消费。试着说：\n\n"
            "- 「今天吃饭花了 35 块」\n"
            "- 「3 个人吃火锅 300 AA」\n"
            "- 「查一下本月预算」\n\n"
            "也可以点输入框上方的「上传小票 / 语音上传 / 手动记一笔」。"
        ),
    }


# ═══════════════════════════════════════════════════════════════
# 成功气泡 / 占位小票
# ═══════════════════════════════════════════════════════════════

def _success_text(amount, category, date_str, note="", draft=None, source="text",
                  demo=True) -> str:
    """确认入库后的只读气泡文案。"""
    lines = ["✅ 已成功记录", ""]
    if draft and draft.get("direction") == "income":
        lines.append("- 方向：收入")
    lines += [
        f"- 金额：¥{float(amount):,.2f}",
        f"- 分类：{category}",
        f"- 日期：{date_str}",
    ]
    if note:
        lines.append(f"- 备注：{note}")
    if draft and draft.get("is_aa"):
        lines.append(
            f"- AA：{draft.get('aa_people')} 人平摊，"
            f"人均 ¥{float(amount):,.2f}"
        )
    lines.append(f"- 来源：{SOURCE_LABELS.get(source, source)}")
    if demo:
        lines += ["", "> 当前为前端 Mock 数据，尚未写入真实账本。"]
    else:
        lines += ["", "> 已写入后端账本。"]
    return "\n".join(lines)


def _placeholder_receipt() -> bytes:
    """生成一张占位小票图片（模拟拍照上传）。"""
    try:
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (420, 260), "#FFFFFF")
        draw = ImageDraw.Draw(image)
        draw.rectangle([1, 1, 418, 258], outline="#DCE3EE", width=3)
        draw.text((28, 30), "MOCK RECEIPT", fill="#1F2937")
        draw.text((28, 62), "Food & Drink", fill="#6B7280")
        draw.line([28, 108, 392, 108], fill="#E5EAF3", width=2)
        draw.text((28, 132), "TOTAL", fill="#1F2937")
        draw.text((316, 132), "¥128.00", fill="#1F2937")
        draw.text((28, 196), "THANK YOU", fill="#9CA3AF")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except (ImportError, OSError, ValueError) as exc:
        # PIL 缺失或图片生成失败时返回一张极小的透明 PNG，保证 UI 不崩
        logger.warning("占位小票生成失败，使用内置 PNG 兜底：%s", exc)
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2n1cAAAAASUVORK5CYII="
        )


# ═══════════════════════════════════════════════════════════════
# 渲染辅助
# ═══════════════════════════════════════════════════════════════

def _type_reply(reply: str) -> None:
    """打字机效果（思考中的 2 秒由外层 spinner 负责）。"""
    placeholder = st.empty()
    shown = ""
    for index in range(0, len(reply), 2):
        shown += reply[index:index + 2]
        placeholder.markdown(shown)
        time.sleep(0.012)


def _scroll_to_bottom() -> None:
    """隐藏 iframe 执行 JS，把聊天区滚到最新消息。"""
    components.html(
        """
        <script>
        (function () {
          try {
            const doc = window.parent.document;
            const anchor = doc.getElementById("chat-bottom-anchor");
            if (anchor) {
              anchor.scrollIntoView({behavior: "smooth", block: "end"});
              return;
            }
            const main = doc.querySelector('[data-testid="stAppScrollToBottomContainer"]');
            if (main) { main.scrollTo({top: main.scrollHeight, behavior: "smooth"}); }
          } catch (e) { /* 跨域时静默失败 */ }
        })();
        </script>
        """,
        height=0,
    )


def _render_attachment(message: dict) -> None:
    if message.get("type") == "image":
        try:
            st.image(message["data"], width=220)
        except Exception:
            st.caption("图片预览失败，但已收到图片。")
        st.caption(f"📷 {message.get('name', '示例小票.png')}")
    elif message.get("type") == "audio":
        st.audio(message["data"], format="audio/wav")
        st.caption("🎤 语音消息")


def _render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("type") in ("image", "audio"):
            _render_attachment(message)
        else:
            st.markdown(message["content"])


def _render_empty_state() -> None:
    st.markdown(
        '<div class="empty-state">'
        '<div class="empty-mark">📒</div>'
        '<div class="empty-title">你好，我是你的 AI 记账助手</div>'
        '<div class="empty-sub">说一句话、拍张小票，或者手动记一笔，都可以。</div>'
        '</div>',
        unsafe_allow_html=True)

    st.markdown('<div class="quick-label">试试这样问</div>', unsafe_allow_html=True)

    _, center, _ = st.columns([0.7, 3, 0.7])
    with center:
        cols = st.columns(2)
        for index, prompt in enumerate(QUICK_PROMPTS):
            with cols[index % 2]:
                if st.button(prompt, key=f"quick_{index}", use_container_width=True):
                    st.session_state.pending_prompt = prompt
                    st.rerun()


def _render_draft_card() -> None:
    """可编辑确认卡片：确认后才写入成功气泡。"""
    draft = st.session_state.get("pending_draft")
    if not draft or draft.get("session_id") != st.session_state.current_session:
        return

    draft_id = draft["id"]
    categories = _categories()
    with st.container(border=True, key="draft_card"):
        st.markdown(
            f'<div class="draft-title">🤖 {draft.get("header", "解析结果，请确认：")}</div>',
            unsafe_allow_html=True)

        # AA 平摊提示（任务 1 的核心提示）
        if draft.get("is_aa"):
            st.warning(
                f"识别到AA，总额 ¥{float(draft.get('aa_total') or 0):g}，"
                f"{draft.get('aa_people')}人平摊，"
                f"已为您折算人均 ¥{float(draft.get('aa_per') or 0):g}"
            )

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "金额（元）",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                value=float(draft.get("amount", 0)),
                key=f"draft_amount_{draft_id}",
            )
        with col2:
            category_index = (categories.index(draft["category"])
                              if draft.get("category") in categories else len(categories) - 1)
            category = st.selectbox(
                "分类", categories, index=category_index,
                key=f"draft_category_{draft_id}",
            )

        col3, col4 = st.columns(2)
        with col3:
            try:
                default_date = datetime.date.fromisoformat(draft.get("date", ""))
            except (TypeError, ValueError):
                default_date = datetime.date.today()
            record_date = st.date_input(
                "日期", value=default_date, key=f"draft_date_{draft_id}")
        with col4:
            note = st.text_input(
                "备注", value=draft.get("note", ""), key=f"draft_note_{draft_id}")

        btn1, btn2, _ = st.columns([1, 1, 2])
        with btn1:
            confirm = st.button(
                "确认入库", type="primary",
                key=f"draft_confirm_{draft_id}", use_container_width=True)
        with btn2:
            reset = st.button(
                "重新填写", key=f"draft_reset_{draft_id}", use_container_width=True)

        if confirm:
            if amount <= 0:
                st.error("金额需要大于 0，请修改后再确认。")
            else:
                demo = _is_demo_mode()
                try:
                    if not demo:
                        with st.spinner("正在写入后端账本..."):
                            _create_expense(
                                amount, category, record_date.isoformat(), note,
                                draft.get("source", "text"), draft)
                    content = _success_text(
                        amount, category, record_date.isoformat(), note,
                        draft=draft, source=draft.get("source", "text"),
                        demo=demo)
                except Exception as exc:
                    st.error(f"⚠️ {_error_text(exc)}")
                    return
                st.session_state.messages.append(
                    {"role": "assistant", "content": content, "type": "success"})
                st.session_state.pop("pending_draft", None)
                st.session_state.force_scroll = True
                st.rerun()

        if reset:
            st.session_state.pop("pending_draft", None)
            st.session_state.messages.append(
                {"role": "assistant", "content": "好的，已放弃本次记录，请重新描述～"})
            st.session_state.force_scroll = True
            st.rerun()


def _render_uploaders() -> None:
    """输入框上方：模拟上传小票 / 语音上传 / 手动记一笔。"""
    round_no = st.session_state.get("upload_round", 0)
    col1, col2, col3, _ = st.columns([1.1, 1.1, 1.35, 2.0])

    with col1:
        if _is_demo_mode():
            if st.button("📷 上传小票", key="mock_receipt",
                         use_container_width=True):
                st.session_state.pending_receipt = True
                st.rerun()
        else:
            with st.popover("📷 上传小票", use_container_width=True):
                uploaded = st.file_uploader(
                    "选择小票图片",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"receipt_upload_{round_no}",
                )
                if uploaded is not None and st.button(
                        "开始识别", key=f"receipt_ocr_{round_no}",
                        use_container_width=True):
                    st.session_state.pending_receipt = {
                        "data": uploaded.getvalue(),
                        "name": uploaded.name,
                    }
                    st.session_state.upload_round = round_no + 1
                    st.rerun()

    with col2:
        with st.popover("🎤 语音上传", use_container_width=True):
            st.caption("录一段话，例如「今天吃饭花了 35」")
            audio = st.audio_input(
                "录音",
                key=f"audio_upload_{round_no}",
                label_visibility="collapsed",
            )
            if audio is not None:
                st.session_state.pending_upload = {
                    "kind": "audio",
                    "data": audio.getvalue(),
                    "name": getattr(audio, "name", "voice.wav"),
                }
                st.session_state.upload_round = round_no + 1
                st.rerun()

    with col3:
        with st.popover("📝 手动记一笔", use_container_width=True):
            with st.form("manual_entry_form", clear_on_submit=True):
                manual_amount = st.number_input(
                    "金额（元）", min_value=0.0, step=1.0,
                    format="%.2f", key="manual_amount")
                manual_category = st.selectbox(
                    "分类", _categories(), key="manual_category")
                manual_date = st.date_input(
                    "日期", value=datetime.date.today(), key="manual_date")
                submitted = st.form_submit_button(
                    "保存", type="primary", use_container_width=True)
            if submitted:
                if manual_amount <= 0:
                    st.error("金额需要大于 0。")
                else:
                    date_str = manual_date.isoformat()
                    demo = _is_demo_mode()
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"📝 手动记一笔：{manual_category} ¥{manual_amount:,.2f}，{date_str}",
                    })
                    if not demo:
                        try:
                            with st.spinner("正在写入后端账本..."):
                                _create_expense(
                                    manual_amount, manual_category, date_str,
                                    "", "manual")
                        except Exception as exc:
                            st.error(f"⚠️ {_error_text(exc)}")
                            return
                    content = _success_text(
                        manual_amount, manual_category, date_str,
                        source="manual", demo=demo)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": content, "type": "success"})
                    st.session_state.force_scroll = True
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# 对话处理
# ═══════════════════════════════════════════════════════════════

def _looks_aa(prompt: str) -> bool:
    return any(keyword in prompt for keyword in ("平摊", "几个人")) or "aa" in prompt.lower()


def _real_parse_result(prompt: str) -> dict:
    """真实模式 NLP：POST /api/v1/expenses/parse → 确认卡片。"""
    data = api_client.parse_transaction_text(prompt) or {}
    raw_amount = data.get("amount")
    category = data.get("category")
    if raw_amount is None:
        return {"intent": "help",
                "reply": data.get("message") or "没有识别出金额，请换一种说法，或改用手动录入。"}
    amount = float(raw_amount)
    spent_at = str(data.get("spent_at") or "")
    date_str = spent_at[:10] if len(spent_at) >= 10 else datetime.date.today().isoformat()
    draft = _build_draft(
        amount, category or "其他", data.get("note") or "", "nlp",
        "已解析这段描述，请确认：",
        direction="expense",
        raw_input=data.get("raw_text") or prompt,
    )
    draft["date"] = date_str
    draft["confidence"] = data.get("confidence")
    if _looks_aa(prompt):
        people = _extract_people(prompt) or 2
        per = amount / people
        draft = _build_draft(
            per, category or "其他", data.get("note") or "", "nlp",
            "已解析这段描述，请确认：",
            direction="expense", is_aa=True,
            aa_total=amount, aa_people=people, aa_per=per,
            raw_input=data.get("raw_text") or prompt,
        )
        draft["date"] = date_str
    return {"intent": "record", "draft": draft}


def _real_chat_result(prompt: str) -> dict:
    """真实模式意图分支：预算 / 分析 / 自然语言记账。"""
    if any(keyword in prompt for keyword in ("预算", "超支", "还剩多少")):
        return {"intent": "budget", "reply": _budget_reply()}
    if any(keyword in prompt for keyword in ("分析", "结构", "统计", "多少")):
        return {"intent": "analysis", "reply": _analysis_reply()}
    return _real_parse_result(prompt)


def _respond_text(prompt: str) -> None:
    prompt = (prompt or "").strip()
    if not prompt:
        return
    messages = st.session_state.messages
    is_first = len(messages) == 0

    messages.append({"role": "user", "content": prompt})
    if is_first:
        _rename_current(prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    demo = _is_demo_mode()
    with st.spinner("AI正在努力解析..."):
        if demo:
            time.sleep(2)
            result = mock_nlu(prompt)
        else:
            try:
                result = _real_chat_result(prompt)
            except Exception as exc:
                result = {"intent": "error",
                          "reply": f"⚠️ {_error_text(exc)}"}

    if result.get("draft"):
        draft = result["draft"]
        draft["session_id"] = st.session_state.current_session
        st.session_state.pending_draft = draft
        st.session_state.force_scroll = True
        # 统一重跑：下一次渲染时输入框锁定、上传入口收起，只展示确认卡片
        st.rerun()

    with st.chat_message("assistant"):
        _type_reply(result.get("reply", ""))
    messages.append({"role": "assistant", "content": result.get("reply", "")})

    if is_first:
        st.rerun()


def _respond_upload(upload: dict) -> None:
    """语音上传：Demo 用 Mock 草稿；真实模式提示本期契约未规划。"""
    messages = st.session_state.messages
    is_first = len(messages) == 0
    message = {
        "role": "user",
        "content": "🎤 语音消息",
        "type": "audio",
        "data": upload["data"],
        "name": upload.get("name"),
    }
    messages.append(message)
    if is_first:
        _rename_current("语音记账")

    with st.chat_message("user"):
        _render_attachment(message)

    if not _is_demo_mode():
        reply = ("语音转写本期接口契约未规划，真实模式暂不可用；"
                 "可先切回「演示模式」预览，或改用文字/小票/手动记账。")
        with st.chat_message("assistant"):
            _type_reply(f"⚠️ {reply}")
        messages.append({"role": "assistant", "content": f"⚠️ {reply}"})
        return

    with st.spinner("AI正在努力解析..."):
        time.sleep(2)
        draft = _build_draft(
            45, "餐饮", "语音识别", "voice",
            "收到语音，已识别以下信息，请确认：",
            direction="expense",
        )
    draft["session_id"] = st.session_state.current_session
    st.session_state.pending_draft = draft
    st.session_state.force_scroll = True
    st.rerun()


def _respond_receipt(upload=None) -> None:
    """小票上传：Demo 用占位图；真实模式调用 /api/v1/receipts/ocr。"""
    messages = st.session_state.messages
    is_first = len(messages) == 0
    demo = _is_demo_mode()

    if demo:
        image = _placeholder_receipt()
        filename = "示例小票.png"
    else:
        if not isinstance(upload, dict) or not upload.get("data"):
            return
        image = upload["data"]
        filename = upload.get("name") or "小票.png"

    message = {
        "role": "user",
        "content": "📷 示例小票" if demo else "📷 小票",
        "type": "image",
        "data": image,
        "name": filename,
    }
    messages.append(message)
    if is_first:
        _rename_current("小票记账")

    with st.chat_message("user"):
        _render_attachment(message)

    with st.spinner("AI正在努力解析..."):
        if demo:
            time.sleep(2)
            draft = _build_draft(
                128, "餐饮", "小票识别", "receipt",
                "收到小票，已识别以下信息，请确认：",
                direction="expense",
            )
        else:
            try:
                result = api_client.ocr_receipt(image, filename) or {}
            except Exception as exc:
                st.error(f"⚠️ {_error_text(exc)}")
                return
            items = result.get("items") or []
            if not items:
                st.error("小票没有识别出可记账的条目，请换一张图片或改用手动录入。")
                return
            item = items[0]
            spent_at = str(item.get("spent_at") or "")
            date_str = spent_at[:10] if len(spent_at) >= 10 else datetime.date.today().isoformat()
            draft = _build_draft(
                float(item.get("amount") or 0),
                item.get("category") or "其他",
                item.get("note") or "",
                "ocr",
                "收到小票，已识别以下信息，请确认：",
                direction="expense",
                raw_input=result.get("raw_text") or "",
            )
            draft["date"] = date_str
            draft["image_path"] = result.get("image_path")
            draft["confidence"] = item.get("confidence")
            if len(items) > 1:
                draft["header"] = f"识别到 {len(items)} 笔，请先确认第 1 笔："

    draft["session_id"] = st.session_state.current_session
    st.session_state.pending_draft = draft
    st.session_state.force_scroll = True
    st.rerun()


# ═══════════════════════════════════════════════════════════════
# 主渲染
# ═══════════════════════════════════════════════════════════════

def _render_chat_view() -> None:
    """对话模式：超支警告 + 历史消息 + 输入 + 确认卡片 + 多模态入口。"""
    ratio = st.session_state.get("budget_ratio", 0.85)
    if ratio > 1.0:  # 任务 4：>1.0 才显示红色警告
        st.error("⚠️ 超支警告：本月已超支！")

    pending_prompt = st.session_state.pop("pending_prompt", None)
    pending_upload = st.session_state.pop("pending_upload", None)
    pending_receipt = st.session_state.pop("pending_receipt", None)

    show_empty = (not st.session_state.messages and
                  pending_prompt is None and
                  pending_upload is None and
                  pending_receipt is None)

    if show_empty:
        _render_empty_state()
    else:
        for item in st.session_state.messages:
            _render_message(item)

    has_draft = bool(st.session_state.get("pending_draft"))
    user_input = st.chat_input(
        "输入你的记账需求...", disabled=has_draft)

    if pending_receipt:
        _respond_receipt(pending_receipt)
    elif pending_upload:
        _respond_upload(pending_upload)
    elif pending_prompt:
        _respond_text(pending_prompt)
    elif user_input:
        _respond_text(user_input)

    # 确认卡片：待确认时放在对话流末尾，用户必须确认/重新填写
    _render_draft_card()

    # 待确认时收起上传入口，聚焦卡片操作
    if not st.session_state.get("pending_draft"):
        _render_uploaders()

    st.markdown('<div id="chat-bottom-anchor"></div>', unsafe_allow_html=True)

    if st.session_state.pop("force_scroll", False):
        _scroll_to_bottom()


# ── 初始化 ──
_init_state()
st.session_state["api_base_url"] = config.API_BASE_URL

# 先按 demo_mode 加载类别与预算；真实模式任何失败都在页面顶部友好提示
demo_mode = _is_demo_mode()
_load_categories()
budget_snapshot = _budget_snapshot()
ratio = float(budget_snapshot["ratio"])
st.session_state["budget_ratio"] = ratio
if not demo_mode:
    st.session_state["budget_ratio_pct"] = min(120, max(0, int(round(ratio * 100))))

new_chat, selected_session = sidebar_ui.render_sidebar(
    sessions=st.session_state.sessions,
    current_id=st.session_state.current_session,
    spent=float(budget_snapshot["spent"]),
    budget=float(budget_snapshot["amount"]),
    demo_mode=demo_mode,
    budget_missing=bool(budget_snapshot.get("missing")),
)
_flush_api_error()

if new_chat:
    current = _current_session()
    if current is None:
        _new_chat()
    elif current.get("messages"):
        _new_chat()
    st.rerun()

if selected_session and selected_session != st.session_state.current_session:
    _switch_chat(selected_session)
    st.session_state.force_scroll = True
    st.rerun()

# 用户气泡颜色
custom_style.inject_bubble_color(st.session_state.get("chat_bubble_color", "#4A7BE8"))

# 模式切换：对话 / 日历 / 统计
view_mode = st.session_state.get("view_mode", "💬 对话")
last_mode = st.session_state.get("_last_view_mode")
if last_mode is not None and last_mode != view_mode and view_mode == "💬 对话":
    st.session_state["force_scroll"] = True
st.session_state["_last_view_mode"] = view_mode

if view_mode == "📅 日历":
    if demo_mode:
        calendar_view.render()
    else:
        today = datetime.date.today()
        try:
            month_records = _load_month_expenses(today.year, today.month)
        except Exception as exc:
            st.error(f"⚠️ {_error_text(exc)}")
            month_records = []
        calendar_view.render(records=month_records, year=today.year, month=today.month)
elif view_mode == "📊 统计":
    stats_view.render()
else:
    _render_chat_view()

# 全局悬浮情绪小球
emotion_mascot.render(st.session_state.get("budget_ratio", 0.85))
