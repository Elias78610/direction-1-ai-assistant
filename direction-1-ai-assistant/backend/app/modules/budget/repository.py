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
        """按月份查询预算，不存在返回 None。"""
        return self.db.scalar(select(Budget).where(Budget.month == month))

    def create(self, month: str, amount: Decimal) -> Budget:
        """新增一条预算记录，事务由 service 提交。"""
        budget = Budget(month=month, amount=amount)
        self.db.add(budget)
        return budget

    def update(self, budget: Budget, amount: Decimal) -> Budget:
        """覆盖已有预算金额，事务由 service 提交。"""
        budget.amount = amount
        return budget

    def delete(self, budget: Budget) -> None:
        """删除预算记录，事务由 service 提交。"""
        self.db.delete(budget)

    def sum_spent(self, start: datetime, end: datetime) -> Decimal:
        """统计时间范围内的支出总额，没有记录时返回 0.00。"""
        stmt = select(func.sum(Expense.amount)).where(
            Expense.spent_at >= start,
            Expense.spent_at <= end,
        )
        value = self.db.scalar(stmt)
        # SQLite 下 SUM 可能返回 float，统一转成 Decimal 并保留两位小数
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
