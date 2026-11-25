from fastapi import APIRouter

from app.api.categories import router as category_router
from app.modules.budget.router import router as budget_router
from app.modules.expense.router import router as expense_router
from app.modules.stats.router import router as stats_router

router = APIRouter(prefix="/api/v1")
router.include_router(expense_router)
router.include_router(budget_router)
router.include_router(category_router)
router.include_router(stats_router)

# 后续在此注册查账、预算等路由


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
