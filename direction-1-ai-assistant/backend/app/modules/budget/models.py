from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Budget(Base):
    """月度预算表，每个月最多一条记录。"""

    __tablename__ = "budgets"
    __table_args__ = {"comment": "月度预算表"}

    month: Mapped[str] = mapped_column(
        String(7), nullable=False, unique=True, index=True,
        comment="预算月份，格式 YYYY-MM")
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False,
        comment="当月预算金额，单位元")
