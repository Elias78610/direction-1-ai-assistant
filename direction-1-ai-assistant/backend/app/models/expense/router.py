from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.expense.models import Expense
from app.models.expense.schemas import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/expenses", tags=["账目"])


@router.post("", response_model=ExpenseOut, status_code=201, summary="新增账目")
def create_expense(data: ExpenseCreate, db: Annotated[Session, Depends(get_db)]):
    """录入一条消费记录，返回入库后的完整数据。"""
    expense = Expense(**data.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("", response_model=list[ExpenseOut], summary="查询账目")
def list_expenses(
    db: Annotated[Session, Depends(get_db)],
    category: Annotated[str | None, Query(description="按类别过滤")] = None,
    start: Annotated[datetime | None, Query(description="消费时间下限（含）")] = None,
    end: Annotated[datetime | None, Query(description="消费时间上限（含）")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="返回条数上限")] = 100,
    offset: Annotated[int, Query(ge=0, description="跳过条数")] = 0,
):
    """按消费时间倒序查询账目，支持类别与时间范围过滤。"""
    stmt = select(Expense).order_by(Expense.spent_at.desc())
    if category:
        stmt = stmt.where(Expense.category == category)
    if start:
        stmt = stmt.where(Expense.spent_at >= start)
    if end:
        stmt = stmt.where(Expense.spent_at <= end)
    stmt = stmt.offset(offset).limit(limit)
    return db.scalars(stmt).all()
