from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Budget(Base):
    """月度预算表，每个月最多一条记录。

    表中只保存预算金额，实际支出不落表，
    查询时再按账目的 spent_at 实时汇总。
    """

    __tablename__ = "budgets"
    __table_args__ = {"comment": "月度预算表"}

    # unique=True 保证同月只有一条预算，重复 PUT 会走更新而不是插入新行
    month: Mapped[str] = mapped_column(
        String(7), nullable=False, unique=True, index=True,
        comment="预算月份，格式 YYYY-MM")
    # 使用 Decimal 存储金额，避免浮点误差
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
        comment="当月预算金额，单位元")
