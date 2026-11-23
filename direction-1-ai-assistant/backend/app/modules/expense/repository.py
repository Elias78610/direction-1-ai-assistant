from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.expense.models import Expense


class ExpenseRepository:
    """账目数据访问层：只负责查询，不做业务判断。"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, expense: Expense) -> Expense:
        self.db.add(expense)
        return expense

    @staticmethod
    def _apply_filters(
        stmt,
        category: str | None,
        start: datetime | None,
        end: datetime | None,
    ):
        """给查询语句追加过滤条件，列表和计数共用，保证两侧口径一致。"""
        if category:
            stmt = stmt.where(Expense.category == category)
        if start:
            stmt = stmt.where(Expense.spent_at >= start)
        if end:
            stmt = stmt.where(Expense.spent_at <= end)
        return stmt

    def get(self, expense_id: int) -> Expense | None:
        """按主键查询单条账目，不存在返回 None。"""
        return self.db.get(Expense, expense_id)

    def update(self, expense: Expense, data: dict) -> Expense:
        """把新字段写入 ORM 对象，事务由 service 统一提交。"""
        for field, value in data.items():
            setattr(expense, field, value)
        return expense

    def delete(self, expense: Expense) -> None:
        """标记删除，事务由 service 统一提交。"""
        self.db.delete(expense)

    def list(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        stmt = select(Expense).order_by(Expense.spent_at.desc())
        stmt = self._apply_filters(stmt, category, start, end)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def count(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        """统计符合过滤条件的账目总数，不受分页影响。"""
        stmt = select(func.count()).select_from(Expense)
        stmt = self._apply_filters(stmt, category, start, end)
        return self.db.scalar(stmt) or 0
