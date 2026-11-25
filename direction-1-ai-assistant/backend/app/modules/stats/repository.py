"""统计查询：只做聚合，不处理业务规则。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.expense.models import Expense


def _as_decimal(value) -> Decimal:
    """兼容 MySQL 的 Decimal 与 SQLite 的 float，统一转成 Decimal 再参与计算。"""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class StatsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _range_where(start: datetime, end: datetime):
        # spent_at 为本地 naive 时间，闭区间，与账目列表的 start/end 语义一致
        return (Expense.spent_at >= start, Expense.spent_at <= end)

    def summary(self, start: datetime, end: datetime) -> tuple[int, Decimal]:
        """返回 (笔数, 总金额)。"""
        total_expr = func.coalesce(func.sum(Expense.amount), 0)
        stmt = (
            select(func.count(Expense.id), total_expr)
            .where(*self._range_where(start, end))
        )
        count, total = self.db.execute(stmt).one()
        return int(count), _as_decimal(total)

    def by_category(
        self, start: datetime, end: datetime
    ) -> list[tuple[str, Decimal, int]]:
        """按类别聚合，金额降序；类别名作为次级排序键保证顺序稳定。"""
        total_expr = func.sum(Expense.amount)
        stmt = (
            select(Expense.category, total_expr, func.count(Expense.id))
            .where(*self._range_where(start, end))
            .group_by(Expense.category)
            .order_by(total_expr.desc(), Expense.category.asc())
        )
        return [
            (str(category), _as_decimal(amount), int(count))
            for category, amount, count in self.db.execute(stmt).all()
        ]

    def trend_by_day(
        self, start: datetime, end: datetime
    ) -> list[tuple[str, Decimal, int]]:
        """按本地日期聚合，返回 [(YYYY-MM-DD, 金额, 笔数)]。"""
        day_expr = func.date(Expense.spent_at)
        total_expr = func.sum(Expense.amount)
        stmt = (
            select(day_expr, total_expr, func.count(Expense.id))
            .where(*self._range_where(start, end))
            .group_by(day_expr)
            .order_by(day_expr.asc())
        )
        # MySQL 的 DATE() 返回 date，SQLite 的 date() 返回字符串，统一取前 10 位
        return [
            (str(period)[:10], _as_decimal(amount), int(count))
            for period, amount, count in self.db.execute(stmt).all()
        ]

    def trend_by_month(
        self, start: datetime, end: datetime
    ) -> list[tuple[str, Decimal, int]]:
        """按年月聚合，返回 [(YYYY-MM, 金额, 笔数)]。

        用 extract 而不是 DATE_FORMAT/strftime，SQLite 与 MySQL 都能编译，
        测试（SQLite）与生产（MySQL）口径一致。
        """
        year_expr = func.extract("year", Expense.spent_at)
        month_expr = func.extract("month", Expense.spent_at)
        total_expr = func.sum(Expense.amount)
        stmt = (
            select(year_expr, month_expr, total_expr, func.count(Expense.id))
            .where(*self._range_where(start, end))
            .group_by(year_expr, month_expr)
            .order_by(year_expr.asc(), month_expr.asc())
        )
        return [
            (f"{int(year):04d}-{int(month):02d}", _as_decimal(amount), int(count))
            for year, month, amount, count in self.db.execute(stmt).all()
        ]
