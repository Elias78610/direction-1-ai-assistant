"""自然语言查账的请求 / 响应契约（对应接口契约 4.3）。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QueryIn(BaseModel):
    """查账问题请求体。"""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., description="自然语言查账问题，如「这个月吃饭花了多少」")


class QueryFilters(BaseModel):
    """解析出的查询条件；识别不出的字段为 null。"""

    start: datetime | None = None
    end: datetime | None = None
    category: str | None = None


class QueryResult(BaseModel):
    """聚合结果：金额为元字符串，两位小数。"""

    total_amount: str
    count: int


class QueryOut(BaseModel):
    """查账响应：answer 为后端拼好的自然语言结论，金额由后端计算。"""

    answer: str
    filters: QueryFilters
    result: QueryResult
