from fastapi import APIRouter

from app.modules.expense.categories import router as category_router
from app.modules.expense.router import router as expense_router

router = APIRouter(prefix="/api/v1")
router.include_router(expense_router)
router.include_router(category_router)

# 后续在此注册分类统计、查账、预算等路由


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
