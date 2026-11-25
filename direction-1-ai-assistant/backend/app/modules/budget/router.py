from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.budget.repository import BudgetRepository
from app.modules.budget.schemas import BudgetOut, BudgetSet
from app.modules.budget.service import BudgetService

router = APIRouter(prefix="/budgets", tags=["预算"])

MonthPath = Annotated[
    str,
    Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="预算月份，格式 YYYY-MM"),
]


def get_service(db: Annotated[Session, Depends(get_db)]) -> BudgetService:
    return BudgetService(BudgetRepository(db), db)


@router.put("/{month}", response_model=BudgetOut, summary="设置或修改月度预算")
def set_budget(
    month: MonthPath,
    data: BudgetSet,
    service: Annotated[BudgetService, Depends(get_service)],
):
    """按月设置预算，重复设置视为更新。"""
    return service.set_budget(month, data.amount)


@router.get("/{month}", response_model=BudgetOut, summary="查询月度预算")
def get_budget(
    month: MonthPath,
    service: Annotated[BudgetService, Depends(get_service)],
):
    """查询预算与执行情况，未设置预算返回 404。"""
    result = service.get_status(month)
    if result is None:
        raise NotFoundError("该月未设置预算")
    return result
