from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.params import EndDatetime
from app.db.session import get_db
from app.modules.expense.repository import ExpenseRepository
from app.modules.expense.schemas import (
    ExpenseCreate,
    ExpenseListOut,
    ExpenseOut,
    ExpenseUpdate,
)
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


@router.get("", response_model=ExpenseListOut, summary="查询账目")
def list_expenses(
    service: Annotated[ExpenseService, Depends(get_service)],
    category: Annotated[str | None, Query(description="按类别过滤")] = None,
    start: Annotated[datetime | None, Query(description="消费时间下限（含）")] = None,
    end: Annotated[EndDatetime, Query(description="消费时间上限（含），传日期时包含当天")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="返回条数上限")] = 100,
    offset: Annotated[int, Query(ge=0, description="跳过条数")] = 0,
):
    """按消费时间倒序查询账目，返回当前页数据与过滤后的总条数。"""
    # 时间范围传反时直接报错，避免返回空列表被误认为「没有记账」
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="开始时间不能晚于结束时间")
    items, total = service.list(
        category=category, start=start, end=end,
        limit=limit, offset=offset,
    )
    return ExpenseListOut(total=total, items=items)


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


@router.put("/{expense_id}", response_model=ExpenseOut, summary="修改账目（部分更新）")
def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    service: Annotated[ExpenseService, Depends(get_service)],
):
    """只更新请求中携带的字段，未传字段保持原值；不存在返回 404。"""
    if not data.model_fields_set:
        raise HTTPException(status_code=400, detail="没有需要修改的字段")
    expense = service.update(expense_id, data)
    if expense is None:
        raise HTTPException(status_code=404, detail="账目不存在")
    return expense


@router.delete("/{expense_id}", status_code=204, summary="删除账目")
def delete_expense(
    expense_id: int,
    service: Annotated[ExpenseService, Depends(get_service)],
) -> None:
    """删除一条账目，不存在返回 404。"""
    if not service.delete(expense_id):
        raise HTTPException(status_code=404, detail="账目不存在")
