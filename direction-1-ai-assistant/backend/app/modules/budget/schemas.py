from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BudgetSet(BaseModel):
    """设置月度预算请求。"""

    # 严格模式：未定义字段直接返回 422，避免前端字段拼错被静默忽略
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(
        ..., gt=0, max_digits=12, decimal_places=2,
        description="当月预算金额，单位：元，必须大于 0", examples=[1000.00])


class BudgetOut(BaseModel):
    """预算与执行情况。

    amount / spent / remaining 均为元字符串，usage_percent 为 0-100 的数字。
    """

    month: str                                   # 预算月份 YYYY-MM
    amount: Decimal                              # 预算金额
    spent: Decimal                               # 当月已花
    remaining: Decimal                           # 剩余，超支时为负数
    usage_percent: float                         # 使用率，如 85.6 表示 85.6%
    status: Literal["normal", "warning", "exceeded"]  # 状态
    message: str                                 # 给前端直接展示的提示文案
