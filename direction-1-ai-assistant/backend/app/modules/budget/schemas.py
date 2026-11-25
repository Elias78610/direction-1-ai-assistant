from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BudgetSet(BaseModel):
    """设置月度预算请求。"""

    # 严格模式：未定义字段直接返回 422
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(
        ..., gt=0, max_digits=12, decimal_places=2,
        description="当月预算金额，单位：元，必须大于 0", examples=[1000.00])


class BudgetOut(BaseModel):
    """预算与执行情况。"""

    month: str
    amount: Decimal
    spent: Decimal
    remaining: Decimal
    usage_percent: float
    status: Literal["normal", "warning", "exceeded"]
    message: str
