import re
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.common.categories import CATEGORIES
from app.core.llm import LlmClient
from app.modules.expense.models import Expense
from app.modules.expense.repository import ExpenseRepository
from app.modules.expense.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    SortField,
    SortOrder,
)

TWO_PLACES = Decimal("0.01")

# 类别关键词 → 固定类别（规则兜底用；与 common/categories.CATEGORIES 口径一致）
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("餐饮", ("饭", "餐", "面", "米", "奶茶", "咖啡", "喝", "吃", "早餐", "午饭", "晚饭", "夜宵", "火锅", "烧烤", "水果")),
    ("交通", ("地铁", "公交", "打车", "出租", "高铁", "火车", "加油", "停车", "骑行", "单车", "车票")),
    ("购物", ("买", "购物", "超市", "衣服", "鞋", "淘宝", "京东", "用品", "日用品")),
    ("娱乐", ("电影", "游戏", "KTV", "唱", "歌", "游玩", "门票", "娱乐")),
    ("居住", ("房租", "水电", "物业", "燃气", "水费", "电费", "房租")),
    ("医疗", ("药", "医院", "看病", "挂号", "体检", "医疗")),
    ("教育", ("书", "课", "学费", "培训", "文具", "教育")),
)

# 时间词 → 相对今天的天数偏移；None 表示取当前时刻
TIME_KEYWORDS: tuple[tuple[str, Optional[int]], ...] = (
    ("前天", -2),
    ("昨天", -1),
    ("今日", 0),
    ("今天", 0),
)

AMOUNT_RE = re.compile(r"\d+(?:\.\d+)?")

_PARSE_SYSTEM = (
    "你是记账助手，从用户一句话中提取消费信息，只输出 JSON，不要任何解释。\n"
    f"固定类别只能取：{'、'.join(CATEGORIES)}。\n"
    "输出字段：\n"
    "- amount: 金额数字（单位：元），识别不出为 null；\n"
    "- category: 必须是上述类别之一，识别不出为 null；\n"
    "- spent_at: 消费时间，格式 YYYY-MM-DDTHH:mm:ss；句子没说时间就用当前时间，识别不出为 null；\n"
    "- note: 简短备注（消费内容），没有为 null。\n"
    "当前时间：{now}"
)


def _now() -> datetime:
    """当前本地时间；单独抽成函数，测试可以固定时间。"""
    return datetime.now().replace(microsecond=0)


def _parse_amount(text: str) -> Optional[Decimal]:
    """规则兜底：提取句子里第一个金额数字；解析失败返回 None。"""
    match = AMOUNT_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group()).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except ArithmeticError:
        return None


def _parse_category(text: str) -> Optional[str]:
    """规则兜底：按关键词命中固定类别；未命中返回 None。"""
    for category, keywords in CATEGORY_KEYWORDS:
        if any(k in text for k in keywords):
            return category
    return None


def _parse_time(text: str, now: datetime) -> datetime:
    """规则兜底：解析时间词；命中昨天/今天等按相对日期取当前时刻，否则取当前时刻。"""
    for word, offset in TIME_KEYWORDS:
        if word in text:
            if offset is None:
                return now
            day = (now + timedelta(days=offset)).replace(
                hour=now.hour, minute=now.minute, second=now.second, microsecond=0
            )
            return day
    return now


def _coerce_amount(value) -> Optional[Decimal]:
    """把模型返回的金额规整为两位小数 Decimal；无法解析返回 None。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        raw = value
    elif isinstance(value, (int, float)):
        raw = Decimal(str(value))
    else:
        match = AMOUNT_RE.search(str(value))
        if not match:
            return None
        raw = Decimal(match.group())
    try:
        return raw.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except ArithmeticError:
        return None


def _coerce_category(value) -> Optional[str]:
    """把模型返回的类别约束到固定枚举；不在枚举内返回 None。"""
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate if candidate in CATEGORIES else None


def _coerce_datetime(value, now: datetime) -> Optional[datetime]:
    """把模型返回的时间规整为 naive datetime；解析失败回退当前时刻。"""
    if value is None:
        return now
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    text = str(value).strip()
    if not text:
        return now
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(microsecond=0)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).replace(microsecond=0)
    except ValueError:
        return now


class ExpenseService:
    """账目业务层：业务规则与事务提交都在这里。"""

    def __init__(self, repo: ExpenseRepository, db: Session):
        self.repo = repo
        self.db = db

    def create(self, data: ExpenseCreate) -> Expense:
        expense = self.repo.create(Expense(**data.model_dump()))
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def get(self, expense_id: int) -> Expense | None:
        """查询单条账目，不存在由路由层返回 404。"""
        return self.repo.get(expense_id)

    def update(self, expense_id: int, data: ExpenseUpdate) -> Expense | None:
        """部分更新账目：只写入请求中显式携带的字段，不存在返回 None。"""
        expense = self.repo.get(expense_id)
        if expense is None:
            return None
        self.repo.update(expense, data.model_dump(exclude_unset=True))
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense_id: int) -> bool:
        """删除账目，成功返回 True，不存在返回 False。"""
        expense = self.repo.get(expense_id)
        if expense is None:
            return False
        self.repo.delete(expense)
        self.db.commit()
        return True

    def list(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: SortField = "spent_at",
        order: SortOrder = "desc",
    ) -> tuple[list[Expense], int]:
        """返回当前页数据和过滤后的总条数。"""
        items = self.repo.list(
            category=category, start=start, end=end,
            limit=limit, offset=offset,
            sort_by=sort_by, order=order,
        )
        total = self.repo.count(category=category, start=start, end=end)
        return items, total

    def parse_nlp(self, text: str) -> dict:
        """自然语言记账解析：优先大模型，失败回退规则；只解析不入库。

        对外响应结构对齐契约 4.2；识别不出的字段返回 null，不猜测。
        """
        now = _now()
        llm = LlmClient()
        llm_result = llm.chat_json(_PARSE_SYSTEM.format(now=now.strftime("%Y-%m-%d %H:%M")), text) if llm.is_configured else None

        if llm_result is not None:
            amount = _coerce_amount(llm_result.get("amount"))
            category = _coerce_category(llm_result.get("category"))
            spent_at = _coerce_datetime(llm_result.get("spent_at"), now)
            note_value = llm_result.get("note")
            note = str(note_value).strip()[:255] if note_value else text[:255]
            llm_hit = True
        else:
            amount = _parse_amount(text)
            category = _parse_category(text)
            spent_at = _parse_time(text, now)
            note = text[:255]
            llm_hit = False

        missing: list[str] = []
        if amount is None:
            missing.append("金额")
        if category is None:
            missing.append("类别")

        if amount is not None and category is not None:
            confidence = 0.95 if llm_hit else 0.9
        elif amount is not None:
            confidence = 0.8 if llm_hit else 0.7
        else:
            confidence = 0.4 if llm_hit else 0.3

        message = None
        if missing:
            message = "未能识别" + "、".join(missing) + "，请在确认卡片中补充"

        return {
            "amount": amount,
            "category": category,
            "spent_at": spent_at,
            "note": note,
            "source": "nlp",
            "raw_text": text,
            "confidence": confidence,
            "message": message,
        }
