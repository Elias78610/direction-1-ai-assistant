from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.expense.models import Expense
from app.modules.expense.repository import ExpenseRepository
from app.modules.expense.schemas import ExpenseCreate, ExpenseUpdate, SortField, SortOrder


class ExpenseService:
    """账目业务层：业务规则与事务提交都在这里。"""

    def __init__(self, repo: ExpenseRepository, db: Session):
        self.repo = repo
        self.db = db

    def create(self, data: ExpenseCreate) -> Expense:
        expense = self.repo.create(Expense(**data.model_dump()))
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def get(self, expense_id: int) -> Expense | None:
        """查询单条账目，不存在由路由层返回 404。"""
        return self.repo.get(expense_id)

    def update(self, expense_id: int, data: ExpenseUpdate) -> Expense | None:
        """部分更新账目：只写入请求中显式携带的字段，不存在返回 None。"""
        expense = self.repo.get(expense_id)
        if expense is None:
            return None
        self.repo.update(expense, data.model_dump(exclude_unset=True))
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense_id: int) -> bool:
        """删除账目，成功返回 True，不存在返回 False。"""
        expense = self.repo.get(expense_id)
        if expense is None:
            return False
        self.repo.delete(expense)
        self.db.commit()
        return True

    def list(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: SortField = "spent_at",
        order: SortOrder = "desc",
    ) -> tuple[list[Expense], int]:
        """返回当前页数据和过滤后的总条数。"""
        items = self.repo.list(
            category=category, start=start, end=end,
            limit=limit, offset=offset,
            sort_by=sort_by, order=order,
        )
        total = self.repo.count(category=category, start=start, end=end)
        return items, total
