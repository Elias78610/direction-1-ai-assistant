from fastapi import APIRouter

from app.common.categories import CATEGORIES

router = APIRouter(prefix="/categories", tags=["类别"])


@router.get("", response_model=list[str], summary="类别列表")
def list_categories() -> list[str]:
    """返回记账可选的消费类别，供前端下拉框、统计和预算使用。"""
    return list(CATEGORIES)
