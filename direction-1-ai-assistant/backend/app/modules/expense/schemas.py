from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["manual", "nlp", "ocr"]


class ExpenseCreate(BaseModel):
    """新增账目请求。"""

    amount: Decimal = Field(
        ..., gt=0, max_digits=12, decimal_places=2,
        description="金额，单位：元", examples=[25.50])
    category: str = Field(
        ..., min_length=1, max_length=50,
        description="消费类别", examples=["餐饮"])
    spent_at: datetime = Field(
        ..., description="消费时间", examples=["2026-11-21T12:30:00"])
    note: str | None = Field(
        None, max_length=255, description="备注")
    source: SourceType = Field(
        "manual", description="来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: str | None = Field(
        None, description="原始输入文本或 OCR 识别内容")


class ExpenseOut(BaseModel):
    """账目返回结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    category: str
    spent_at: datetime
    note: str | None
    source: str
    raw_text: str | None
    user_id: int | None
    created_time: datetime
    updated_time: datetime
