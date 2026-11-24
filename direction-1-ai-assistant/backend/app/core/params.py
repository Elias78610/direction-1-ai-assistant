"""查询参数处理：统一时间范围的边界语义。"""

from datetime import date, datetime, time
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator


def _date_to_end_of_day(value):
    """end 传纯日期（如 2026-11-30）时扩展到当天 23:59:59。

    传了具体时间（如 2026-11-30T12:00:00）则保持原值，按精确时间比较。
    """
    if isinstance(value, str) and len(value) == 10:
        day = date.fromisoformat(value)
        return datetime.combine(day, time(23, 59, 59))
    return value


def _reject_aware(value: datetime | None) -> datetime | None:
    """拒绝带时区的时间，统一使用本地 naive 时间。

    aware 与 naive 直接比较会抛 TypeError，混用还可能悄悄丢掉时区。
    """
    if value is not None and value.tzinfo is not None:
        raise ValueError("时间不能带时区，请使用 YYYY-MM-DDTHH:mm:ss 的本地时间格式")
    return value


# 请求体中的时间字段使用，如 Expense.spent_at
NaiveDatetime = Annotated[datetime, AfterValidator(_reject_aware)]

# 查询参数 start：不允许带时区
StartDatetime = Annotated[datetime | None, AfterValidator(_reject_aware)]

# 供查询参数 end 使用：日期写法包含当天，时间写法精确匹配；两种写法都不允许带时区。
# 统计接口的时间范围也应复用这些类型，保持口径一致。
EndDatetime = Annotated[
    datetime | None,
    BeforeValidator(_date_to_end_of_day),
    AfterValidator(_reject_aware),
]
