from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.expense.models import Expense
from app.modules.expense.repository import ExpenseRepository
from app.modules.expense.schemas import ExpenseCreate


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

    def list(
        self,
        category: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Expense]:
        return self.repo.list(
            category=category, start=start, end=end,
            limit=limit, offset=offset,
        )
