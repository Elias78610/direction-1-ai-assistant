from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.params import EndDatetime, StartDatetime
from app.db.session import get_db
from app.modules.stats.repository import StatsRepository
from app.modules.stats.schemas import (
    StatsCategoriesOut,
    StatsSummaryOut,
    StatsTrendOut,
)
from app.modules.stats.service import StatsService

router = APIRouter(prefix="/stats", tags=["统计"])

StartParam = Annotated[
    StartDatetime,
    Query(description="统计开始时间（含），不能带时区；只传日期时按当天 00:00:00 处理"),
]
EndParam = Annotated[
    EndDatetime,
    Query(description="统计结束时间（含），不能带时区；传日期时包含当天 23:59:59"),
]
Granularity = Annotated[
    Literal["day", "month"],
    Query(description="趋势粒度：day 按天 / month 按月，默认 day"),
]


def get_service(db: Annotated[Session, Depends(get_db)]) -> StatsService:
    return StatsService(StatsRepository(db))


@router.get("/summary", response_model=StatsSummaryOut, summary="消费总览")
def get_summary(
    service: Annotated[StatsService, Depends(get_service)],
    start: StartParam = None,
    end: EndParam = None,
):
    """按时间范围汇总总支出、笔数与笔均金额；不传时间范围时默认本月。"""
    return service.summary(start, end)


@router.get(
    "/categories",
    response_model=StatsCategoriesOut,
    summary="分类占比",
)
def get_categories(
    service: Annotated[StatsService, Depends(get_service)],
    start: StartParam = None,
    end: EndParam = None,
):
    """按类别汇总金额、笔数与占比，金额降序，供饼图使用。"""
    return service.categories(start, end)


@router.get("/trend", response_model=StatsTrendOut, summary="消费趋势")
def get_trend(
    service: Annotated[StatsService, Depends(get_service)],
    start: StartParam = None,
    end: EndParam = None,
    granularity: Granularity = "day",
):
    """按天或按月汇总金额与笔数，缺失周期补 0，供折线图使用。"""
    return service.trend(start, end, granularity)
