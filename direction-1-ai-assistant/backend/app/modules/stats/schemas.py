"""统计接口响应模型。

金额统一为「元、两位小数字符串」，与账目接口口径一致；占比为 0~1 的小数，
保留四位小数，避免前端拿百分比字符串再解析。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StatsSummaryOut(BaseModel):
    """总览：时间范围内的总支出、笔数、笔均。"""

    start: datetime = Field(description="统计开始时间（含）")
    end: datetime = Field(description="统计结束时间（含）")
    total_amount: str = Field(description="总支出，单位元，固定两位小数")
    count: int = Field(description="消费笔数")
    avg_amount: str = Field(description="笔均金额，单位元，固定两位小数")


class CategoryStatOut(BaseModel):
    """单个类别的统计结果。"""

    category: str = Field(description="消费类别，取值见 CATEGORIES")
    amount: str = Field(description="该类支出合计，单位元")
    count: int = Field(description="该类笔数")
    ratio: float = Field(description="金额占比，0~1，保留四位小数")


class StatsCategoriesOut(BaseModel):
    """分类占比：按金额降序，仅返回有数据的类别。"""

    start: datetime
    end: datetime
    total_amount: str = Field(description="全部分类合计，单位元")
    items: list[CategoryStatOut]


class TrendPointOut(BaseModel):
    """趋势上的一个点。"""

    period: str = Field(description="统计周期：day 为 YYYY-MM-DD，month 为 YYYY-MM")
    amount: str = Field(description="该周期支出合计，单位元")
    count: int = Field(description="该周期笔数")


class StatsTrendOut(BaseModel):
    """趋势：缺失周期补 0，保证前端可以直接连成折线。"""

    granularity: Literal["day", "month"]
    start: datetime
    end: datetime
    points: list[TrendPointOut]
