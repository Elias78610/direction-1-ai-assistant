from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.expense.models import Expense


class ExpenseRepository:
    """账目数据访问层：只负责查询，不做业务判断。"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, expense: Expense) -> Expense:
        self.db.add(expense)
        return expense

    def get(self, expense_id: int) -> Expense | None:
        """按主键查询单条账目，不存在返回 None。"""
        return self.db.get(Expense, expense_id)

    def list(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        stmt = select(Expense).order_by(Expense.spent_at.desc())
        if category:
            stmt = stmt.where(Expense.category == category)
        if start:
            stmt = stmt.where(Expense.spent_at >= start)
        if end:
            stmt = stmt.where(Expense.spent_at <= end)
        stmt = stmt.offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())
