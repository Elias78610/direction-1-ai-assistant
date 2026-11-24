from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.common.categories import CATEGORIES
from app.core.params import NaiveDatetime


def _validate_category(value: str) -> str:
    """类别必须来自固定列表，保证统计数据与前端下拉框口径一致。"""
    if value not in CATEGORIES:
        raise ValueError(f"类别必须是以下之一：{'、'.join(CATEGORIES)}")
    return value


# 字符串约束：先去掉首尾空白（包括全角空格），再校验长度和类别。
# 使用 Annotated 定义一次，多个字段复用，避免每个字段重复写 validator。
CategoryName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
    AfterValidator(_validate_category),
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

# 列表接口允许的排序字段与方向，由路由参数校验，repository 白名单映射
SortField = Literal["id", "spent_at", "amount", "category", "created_time"]
SortOrder = Literal["asc", "desc"]


class ExpenseCreate(BaseModel):
    """新增账目请求。"""

    # 严格模式：请求里出现未定义字段直接返回 422，避免字段被静默丢弃
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(
        ..., gt=0, max_digits=12, decimal_places=2,
        description="金额，单位：元", examples=[25.50])
    category: CategoryName = Field(
        ..., description="消费类别，必须是固定类别之一，自动去除首尾空格",
        examples=["餐饮"])
    spent_at: NaiveDatetime = Field(
        ..., description="消费时间，不能带时区", examples=["2026-11-21T12:30:00"])
    note: NoteText | None = Field(
        None, description="备注，自动去除首尾空格，空字符串存为 null")
    source: SourceType = Field(
        "manual", description="来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: RawText | None = Field(
        None, description="原始输入文本或 OCR 识别内容，自动去除首尾空格")
    image_path: str | None = Field(
        None, max_length=255,
        description="小票或截图路径，仅 OCR 确认入库时传，必须在 data/uploads/ 下")

    @field_validator("image_path")
    @classmethod
    def validate_image_path(cls, value: str | None) -> str | None:
        """只允许 data/uploads/ 下的相对路径，避免写入任意路径。"""
        if value is None:
            return None
        if value.startswith("/") or "\\" in value or ".." in value.split("/"):
            raise ValueError("image_path 必须是 data/uploads/ 下的相对路径")
        if not value.startswith("data/uploads/"):
            raise ValueError("image_path 必须以 data/uploads/ 开头")
        return value

    @field_validator("note", "raw_text", mode="after")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        """去空格后为空的可选文本统一转成 None，避免库里出现空字符串。"""
        return value or None


class ExpenseUpdate(BaseModel):
    """修改账目请求：只传需要修改的字段，未传字段保持原值。

    显式传 null 会清空可空字段（note / raw_text）；
    完全省略则不改动，避免前端只改金额时把 source、备注和原文覆盖掉。
    """

    # 严格模式：请求里出现未定义字段直接返回 422
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(
        None, gt=0, max_digits=12, decimal_places=2,
        description="金额，单位：元")
    category: CategoryName | None = Field(
        None, description="消费类别，必须是固定类别之一，自动去除首尾空格")
    spent_at: NaiveDatetime | None = Field(
        None, description="消费时间，不能带时区")
    note: NoteText | None = Field(
        None, description="备注，自动去除首尾空格，空字符串存为 null")
    source: SourceType | None = Field(
        None, description="来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: RawText | None = Field(
        None, description="原始输入文本或 OCR 识别内容，自动去除首尾空格")

    @field_validator("amount", "category", "spent_at", "source", mode="before")
    @classmethod
    def required_not_null(cls, value):
        """必填字段不允许显式传 null；未传的字段有默认值，不会触发该校验。"""
        if value is None:
            raise ValueError("该字段不能为 null")
        return value

    @field_validator("note", "raw_text", mode="after")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        """去空格后为空的可选文本统一转成 None。"""
        return value or None


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
    image_path: str | None
    created_time: datetime
    updated_time: datetime


class ExpenseListOut(BaseModel):
    """账目分页响应：total 为过滤后的总条数，items 为当前页数据。"""

    total: int
    items: list[ExpenseOut]
