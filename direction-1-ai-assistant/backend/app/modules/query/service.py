"""自然语言查账业务层：问题解析、时间范围与结论文案。"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.modules.query.repository import QueryRepository

TWO_PLACES = Decimal("0.01")

# 类别关键词 → 固定类别（与 common/categories.CATEGORIES 口径一致）
CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("餐饮", ("饭", "餐", "面", "奶茶", "咖啡", "吃", "喝", "午饭", "晚饭", "早餐", "水果")),
    ("交通", ("地铁", "公交", "打车", "出租", "高铁", "火车", "加油", "停车", "车票")),
    ("购物", ("买", "购物", "超市", "衣服", "鞋", "用品")),
    ("娱乐", ("电影", "游戏", "KTV", "唱", "歌", "游玩", "门票")),
    ("居住", ("房租", "水电", "物业", "燃气", "水费", "电费")),
    ("医疗", ("药", "医院", "看病", "挂号", "体检")),
    ("教育", ("书", "课", "学费", "培训", "文具")),
)


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _format_amount(value: Decimal) -> str:
    return str(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def _parse_category(question: str) -> str | None:
    for category, keywords in CATEGORY_KEYWORDS:
        if any(k in question for k in keywords):
            return category
    return None


def _parse_range(question: str, now: datetime) -> tuple[datetime, datetime, str]:
    """解析时间范围，返回 (start, end, 周期描述)；默认本月。"""
    if "上月" in question or "上个月" in question:
        first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_prev = first_this_month - timedelta(seconds=1)
        first_prev = last_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return first_prev, last_prev, "上月"

    if "昨天" in question:
        start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
        return start, end, "昨天"

    if "今天" in question or "今日" in question:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, now, "今天"

    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now, "本月"


class QueryService:
    """查账业务层：解析问题条件，聚合账目并生成自然语言结论。"""

    def __init__(self, repo: QueryRepository, db: Session):
        self.repo = repo
        self.db = db

    def ask(self, question: str) -> dict:
        now = _now()
        category = _parse_category(question)
        start, end, period = _parse_range(question, now)

        count, total = self.repo.aggregate(category=category, start=start, end=end)
        amount_text = _format_amount(total)

        if count == 0:
            category_part = f"{category}" if category else ""
            answer = f"{period}没有记录{category_part}账目。"
        elif category:
            answer = f"{period}{category}共花费 {amount_text} 元，共 {count} 笔。"
        else:
            answer = f"{period}共花费 {amount_text} 元，共 {count} 笔。"

        return {
            "answer": answer,
            "filters": {"start": start, "end": end, "category": category},
            "result": {"total_amount": amount_text, "count": count},
        }
