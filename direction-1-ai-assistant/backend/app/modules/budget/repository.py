from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.budget.models import Budget
from app.modules.expense.models import Expense


class BudgetRepository:
    """预算数据访问层：预算读写与当月支出汇总。"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, month: str) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.month == month))

    def create(self, month: str, amount: Decimal) -> Budget:
        budget = Budget(month=month, amount=amount)
        self.db.add(budget)
        return budget

    def update(self, budget: Budget, amount: Decimal) -> Budget:
        budget.amount = amount
        return budget

    def sum_spent(self, start: datetime, end: datetime) -> Decimal:
        """统计时间范围内的支出总额，没有记录时返回 0.00。"""
        stmt = select(func.sum(Expense.amount)).where(
            Expense.spent_at >= start,
            Expense.spent_at <= end,
        )
        value = self.db.scalar(stmt)
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
