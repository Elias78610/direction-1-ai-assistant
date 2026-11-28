"""查账聚合查询：只按条件统计笔数与金额，不做业务判断。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.expense.models import Expense


def _as_decimal(value) -> Decimal:
    """兼容 MySQL 的 Decimal 与 SQLite 的 float，统一转成 Decimal。"""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class QueryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def aggregate(
        self,
        category: str | None,
        start: datetime | None,
        end: datetime | None,
    ) -> tuple[int, Decimal]:
        """按类别 + 时间范围聚合，返回 (笔数, 总金额)。"""
        total_expr = func.coalesce(func.sum(Expense.amount), 0)
        stmt = select(func.count(Expense.id), total_expr)
        if category:
            stmt = stmt.where(Expense.category == category)
        if start:
            stmt = stmt.where(Expense.spent_at >= start)
        if end:
            stmt = stmt.where(Expense.spent_at <= end)
        count, total = self.db.execute(stmt).one()
        return int(count), _as_decimal(total)
