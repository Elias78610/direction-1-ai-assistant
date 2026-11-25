"""统计业务逻辑：时间范围解析、金额格式化、占比与补零。"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.core.exceptions import AppException
from app.modules.stats.repository import StatsRepository
from app.modules.stats.schemas import (
    CategoryStatOut,
    StatsCategoriesOut,
    StatsSummaryOut,
    StatsTrendOut,
    TrendPointOut,
)

# 趋势点的上限：按天最多一年，按月最多十年，避免一次请求生成超大数组
MAX_TREND_DAYS = 366
MAX_TREND_MONTHS = 120

TWO_PLACES = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")


def _now() -> datetime:
    """当前本地时间；单独抽成函数，测试可以固定时间。"""
    return datetime.now().replace(microsecond=0)


def format_amount(value: Decimal) -> str:
    """金额转成固定两位小数的字符串，四舍五入。"""
    return str(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def _ratio(amount: Decimal, total: Decimal) -> float:
    """占比 0~1，保留四位小数；总金额为 0 时返回 0。"""
    if total <= 0:
        return 0.0
    return float((amount / total).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP))


def _month_span(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _iter_months(start: date, end: date) -> Iterator[date]:
    current = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while current <= last:
        yield current
        current = date(
            current.year + current.month // 12,
            current.month % 12 + 1,
            1,
        )


@dataclass(frozen=True)
class TimeRange:
    start: datetime
    end: datetime


class StatsService:
    def __init__(self, repo: StatsRepository) -> None:
        self.repo = repo

    def resolve_range(
        self, start: datetime | None, end: datetime | None
    ) -> TimeRange:
        """按契约解析时间范围。

        - 都不传：本月 1 日 00:00:00 至当前时间
        - 只传 start：end 取当前时间
        - 只传 end：start 取 end 所在月 1 日 00:00:00
        - start > end：400 BAD_REQUEST
        """
        now = _now()
        if start is None and end is None:
            start = datetime(now.year, now.month, 1)
            end = now
        elif start is None:
            assert end is not None  # 供类型检查使用
            start = datetime(end.year, end.month, 1)
        elif end is None:
            end = now

        if start > end:
            raise AppException(
                code="BAD_REQUEST",
                message="开始时间不能晚于结束时间",
                status_code=400,
            )
        return TimeRange(start=start, end=end)

    def summary(
        self, start: datetime | None, end: datetime | None
    ) -> StatsSummaryOut:
        rng = self.resolve_range(start, end)
        count, total = self.repo.summary(rng.start, rng.end)
        average = total / count if count else Decimal("0")
        return StatsSummaryOut(
            start=rng.start,
            end=rng.end,
            total_amount=format_amount(total),
            count=count,
            avg_amount=format_amount(average),
        )

    def categories(
        self, start: datetime | None, end: datetime | None
    ) -> StatsCategoriesOut:
        rng = self.resolve_range(start, end)
        rows = self.repo.by_category(rng.start, rng.end)
        total = sum((amount for _, amount, _ in rows), start=Decimal("0"))
        items = [
            CategoryStatOut(
                category=category,
                amount=format_amount(amount),
                count=count,
                ratio=_ratio(amount, total),
            )
            for category, amount, count in rows
        ]
        return StatsCategoriesOut(
            start=rng.start,
            end=rng.end,
            total_amount=format_amount(total),
            items=items,
        )

    def trend(
        self,
        start: datetime | None,
        end: datetime | None,
        granularity: Literal["day", "month"],
    ) -> StatsTrendOut:
        rng = self.resolve_range(start, end)
        if granularity == "day":
            self._check_day_span(rng)
            rows = self.repo.trend_by_day(rng.start, rng.end)
            by_period = {period: (amount, count) for period, amount, count in rows}
            points = []
            current = rng.start.date()
            last = rng.end.date()
            while current <= last:
                period = current.isoformat()
                amount, count = by_period.get(period, (Decimal("0"), 0))
                points.append(
                    TrendPointOut(
                        period=period,
                        amount=format_amount(amount),
                        count=count,
                    )
                )
                current += timedelta(days=1)
        else:
            self._check_month_span(rng)
            rows = self.repo.trend_by_month(rng.start, rng.end)
            by_period = {period: (amount, count) for period, amount, count in rows}
            points = []
            for month in _iter_months(rng.start.date(), rng.end.date()):
                period = month.strftime("%Y-%m")
                amount, count = by_period.get(period, (Decimal("0"), 0))
                points.append(
                    TrendPointOut(
                        period=period,
                        amount=format_amount(amount),
                        count=count,
                    )
                )

        return StatsTrendOut(
            granularity=granularity,
            start=rng.start,
            end=rng.end,
            points=points,
        )

    @staticmethod
    def _check_day_span(rng: TimeRange) -> None:
        days = (rng.end.date() - rng.start.date()).days + 1
        if days > MAX_TREND_DAYS:
            raise AppException(
                code="BAD_REQUEST",
                message=(
                    f"按天统计的时间范围不能超过 {MAX_TREND_DAYS} 天，"
                    "请缩短范围或改用 granularity=month"
                ),
                status_code=400,
            )

    @staticmethod
    def _check_month_span(rng: TimeRange) -> None:
        months = _month_span(rng.start.date(), rng.end.date())
        if months > MAX_TREND_MONTHS:
            raise AppException(
                code="BAD_REQUEST",
                message=f"按月统计的时间范围不能超过 {MAX_TREND_MONTHS} 个月",
                status_code=400,
            )
