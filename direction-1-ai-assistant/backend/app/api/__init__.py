from fastapi import APIRouter

from app.api.categories import router as category_router
from app.modules.budget.router import router as budget_router
from app.modules.expense.router import router as expense_router
from app.modules.query.router import router as query_router
from app.modules.receipts.router import router as receipts_router
from app.modules.stats.router import router as stats_router

router = APIRouter(prefix="/api/v1")
router.include_router(expense_router)
router.include_router(budget_router)
router.include_router(category_router)
router.include_router(stats_router)
router.include_router(query_router)
router.include_router(receipts_router)


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
