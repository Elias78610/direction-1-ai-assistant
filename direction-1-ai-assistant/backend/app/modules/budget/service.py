import calendar
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.modules.budget.repository import BudgetRepository
from app.modules.budget.schemas import BudgetOut

# 使用率达到 80% 进入预警；超过 100% 才算超支
WARNING_RATIO = Decimal("0.8")
PERCENT = Decimal("0.01")


class BudgetService:
    """预算业务层：月份边界、使用比例、状态与提示文案。"""

    def __init__(self, repo: BudgetRepository, db: Session):
        self.repo = repo
        self.db = db

    def set_budget(self, month: str, amount: Decimal) -> BudgetOut:
        """设置预算，同月重复设置视为更新。"""
        # 先校验月份再写库：非法月份必须在产生任何写入之前失败，
        # 否则 commit 后再计算状态会留下脏数据
        self._month_range(month)

        budget = self.repo.get(month)
        if budget is None:
            self.repo.create(month, amount)   # 首次设置：新增
        else:
            self.repo.update(budget, amount)  # 已存在：覆盖金额
        self.db.commit()

        # 写入后统一走查询逻辑，返回同样的执行情况结构
        result = self.get_status(month)
        # 刚写入的预算一定存在
        assert result is not None
        return result

    def get_status(self, month: str) -> BudgetOut | None:
        """查询预算与执行情况，未设置预算返回 None。"""
        budget = self.repo.get(month)
        if budget is None:
            return None

        # 按自然月统计，包含最后一天 23:59:59
        start, end = self._month_range(month)
        spent = self.repo.sum_spent(start, end)
        amount = budget.amount
        remaining = amount - spent
        # 使用率保留两位小数，避免前端看到 85.59999
        usage = (spent / amount * 100).quantize(PERCENT, rounding=ROUND_HALF_UP)

        if spent > amount:
            # 超出预算：remaining 为负数，取反后展示超支金额
            status = "exceeded"
            message = f"本月已超支 {(-remaining):.2f} 元"
        elif spent >= amount * WARNING_RATIO:
            # 使用率达到 80%，但还没超过预算
            status = "warning"
            message = f"本月预算已使用 {usage:.2f}%，注意控制支出"
        else:
            # 使用率低于 80%
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
        """YYYY-MM → 当月第一天 00:00:00 到月末 23:59:59。

        路由层已经用正则限制格式，这里再做一层防御，
        即使 service 被直接调用也不会因为非法年份抛 500。
        """
        try:
            year, mon = int(month[:4]), int(month[5:7])
            first = date(year, mon, 1)
            last_day = calendar.monthrange(year, mon)[1]
        except (TypeError, ValueError) as exc:
            raise AppException(
                code="BAD_REQUEST",
                message="预算月份不合法，格式应为 YYYY-MM",
                status_code=400,
            ) from exc

        return (
            datetime.combine(first, time.min),
            datetime.combine(date(year, mon, last_day), time(23, 59, 59)),
        )
