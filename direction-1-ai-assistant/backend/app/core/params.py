"""查询参数处理：统一时间范围的边界语义。"""

from datetime import date, datetime, time
from typing import Annotated

from pydantic import BeforeValidator


def _date_to_end_of_day(value):
    """end 传纯日期（如 2026-11-30）时扩展到当天 23:59:59。

    传了具体时间（如 2026-11-30T12:00:00）则保持原值，按精确时间比较。
    """
    if isinstance(value, str) and len(value) == 10:
        day = date.fromisoformat(value)
        return datetime.combine(day, time(23, 59, 59))
    return value


# 供查询参数 end 使用：日期写法包含当天，时间写法精确匹配。
# 统计接口的时间范围也应复用这个类型，保持口径一致。
EndDatetime = Annotated[datetime | None, BeforeValidator(_date_to_end_of_day)]
