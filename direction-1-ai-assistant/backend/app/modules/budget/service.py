import calendar
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.modules.budget.repository import BudgetRepository
from app.modules.budget.schemas import BudgetOut

WARNING_RATIO = Decimal("0.8")
PERCENT = Decimal("0.01")


class BudgetService:
    """预算业务层：月份边界、使用比例、状态与提示文案。"""

    def __init__(self, repo: BudgetRepository, db: Session):
        self.repo = repo
        self.db = db

    def set_budget(self, month: str, amount: Decimal) -> BudgetOut:
        """设置预算，同月重复设置视为更新。"""
        budget = self.repo.get(month)
        if budget is None:
            self.repo.create(month, amount)
        else:
            self.repo.update(budget, amount)
        self.db.commit()

        result = self.get_status(month)
        # 刚写入的预算一定存在
        assert result is not None
        return result

    def get_status(self, month: str) -> BudgetOut | None:
        """查询预算与执行情况，未设置预算返回 None。"""
        budget = self.repo.get(month)
        if budget is None:
            return None

        start, end = self._month_range(month)
        spent = self.repo.sum_spent(start, end)
        amount = budget.amount
        remaining = amount - spent
        usage = (spent / amount * 100).quantize(PERCENT, rounding=ROUND_HALF_UP)

        if spent > amount:
            status = "exceeded"
            message = f"本月已超支 {(-remaining):.2f} 元"
        elif spent >= amount * WARNING_RATIO:
            status = "warning"
            message = f"本月预算已使用 {usage:.2f}%，注意控制支出"
        else:
            status = "normal"
            message = f"本月预算剩余 {remaining:.2f} 元"

        return BudgetOut(
            month=month,
            amount=amount,
            spent=spent,
            remaining=remaining,
            usage_percent=float(usage),
            status=status,
            message=message,
        )

    @staticmethod
    def _month_range(month: str) -> tuple[datetime, datetime]:
        """YYYY-MM → 当月第一天 00:00:00 到月末 23:59:59。"""
        year, mon = int(month[:4]), int(month[5:7])
        first = date(year, mon, 1)
        last_day = calendar.monthrange(year, mon)[1]
        return (
            datetime.combine(first, time.min),
            datetime.combine(date(year, mon, last_day), time(23, 59, 59)),
        )
