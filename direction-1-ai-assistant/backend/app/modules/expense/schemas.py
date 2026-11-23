from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

# 字符串约束：先去掉首尾空白（包括全角空格），再校验长度。
# 使用 Annotated 定义一次，多个字段复用，避免每个字段重复写 validator。
CategoryName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
NoteText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=255),
]
RawText = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
]

SourceType = Literal["manual", "nlp", "ocr"]


class ExpenseCreate(BaseModel):
    """新增账目请求。"""

    amount: Decimal = Field(
        ..., gt=0, max_digits=12, decimal_places=2,
        description="金额，单位：元", examples=[25.50])
    category: CategoryName = Field(
        ..., description="消费类别，自动去除首尾空格，全空格会被拒绝",
        examples=["餐饮"])
    spent_at: datetime = Field(
        ..., description="消费时间", examples=["2026-11-21T12:30:00"])
    note: NoteText | None = Field(
        None, description="备注，自动去除首尾空格，空字符串存为 null")
    source: SourceType = Field(
        "manual", description="来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: RawText | None = Field(
        None, description="原始输入文本或 OCR 识别内容，自动去除首尾空格")

    @field_validator("note", "raw_text", mode="after")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        """去空格后为空的可选文本统一转成 None，避免库里出现空字符串。"""
        return value or None


class ExpenseUpdate(ExpenseCreate):
    """修改账目请求：字段与新增一致，采用全量更新。"""


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
