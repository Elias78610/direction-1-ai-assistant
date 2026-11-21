from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

# 后续在此注册记账、分类统计、查账、预算等路由


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}
