from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.modules.budget.repository import BudgetRepository
from app.modules.budget.schemas import MONTH_PATTERN, BudgetOut, BudgetSet
from app.modules.budget.service import BudgetService

router = APIRouter(prefix="/budgets", tags=["预算"])

# 路径参数校验：只接受 1900-2099 年的 YYYY-MM，例如 2026-11。
# 限制年份是为了避免 0000 这类 Python date 不支持的年份进入 service。
MonthPath = Annotated[
    str,
    Path(
        pattern=MONTH_PATTERN,
        description="预算月份，格式 YYYY-MM，年份范围 1900-2099",
    ),
]


def get_service(db: Annotated[Session, Depends(get_db)]) -> BudgetService:
    """依赖注入：每次请求创建独立的预算 service。"""
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


@router.delete("/{month}", status_code=204, summary="取消月度预算")
def delete_budget(
    month: MonthPath,
    service: Annotated[BudgetService, Depends(get_service)],
) -> None:
    """取消某月预算，未设置预算返回 404。"""
    if not service.delete_budget(month):
        raise NotFoundError("该月未设置预算")
