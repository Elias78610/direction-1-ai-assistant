from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.expense.repository import ExpenseRepository
from app.modules.expense.schemas import ExpenseCreate, ExpenseOut
from app.modules.expense.service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["账目"])


def get_service(db: Annotated[Session, Depends(get_db)]) -> ExpenseService:
    return ExpenseService(ExpenseRepository(db), db)


@router.post("", response_model=ExpenseOut, status_code=201, summary="新增账目")
def create_expense(
    data: ExpenseCreate,
    service: Annotated[ExpenseService, Depends(get_service)],
):
    """录入一条消费记录，返回入库后的完整数据。"""
    return service.create(data)


@router.get("", response_model=list[ExpenseOut], summary="查询账目")
def list_expenses(
    service: Annotated[ExpenseService, Depends(get_service)],
    category: Annotated[str | None, Query(description="按类别过滤")] = None,
    start: Annotated[datetime | None, Query(description="消费时间下限（含）")] = None,
    end: Annotated[datetime | None, Query(description="消费时间上限（含）")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="返回条数上限")] = 100,
    offset: Annotated[int, Query(ge=0, description="跳过条数")] = 0,
):
    """按消费时间倒序查询账目，支持类别与时间范围过滤。"""
    return service.list(
        category=category, start=start, end=end,
        limit=limit, offset=offset,
    )


@router.get("/{expense_id}", response_model=ExpenseOut, summary="账目详情")
def get_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_service)],
):
    """按 id 查询单条账目，不存在返回 404。"""
    expense = service.get(expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="账目不存在")
    return expense
