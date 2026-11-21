from fastapi import APIRouter

from app.models.expense.router import router as expense_router

router = APIRouter(prefix="/api/v1")
router.include_router(expense_router)

# 后续在此注册分类统计、查账、预算等路由


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
