from fastapi import APIRouter

from app.modules.expense.constants import CATEGORIES

router = APIRouter(prefix="/categories", tags=["类别"])

# 固定类别列表：统计、预算和前端下拉框都以 constants.py 为准。
# 后续如需自定义类别，可改为数据库表，接口路径保持不变。


@router.get("", response_model=list[str], summary="类别列表")
def list_categories() -> list[str]:
    """返回记账可选的消费类别，供前端下拉框和统计使用。"""
    return list(CATEGORIES)
