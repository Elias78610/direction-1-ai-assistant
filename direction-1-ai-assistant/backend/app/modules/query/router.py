from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.query.repository import QueryRepository
from app.modules.query.schemas import QueryIn, QueryOut
from app.modules.query.service import QueryService

router = APIRouter(prefix="/query", tags=["自然语言查账"])


def get_service(db: Annotated[Session, Depends(get_db)]) -> QueryService:
    return QueryService(QueryRepository(db), db)


@router.post("", response_model=QueryOut, summary="自然语言查账")
def ask_query(
    data: QueryIn,
    service: Annotated[QueryService, Depends(get_service)],
):
    """解析自然语言问题，按类别与时间范围聚合账目，返回结论文案。"""
    return service.ask(data.question)
