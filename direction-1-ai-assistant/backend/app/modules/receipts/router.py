from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.modules.receipts.schemas import ReceiptOcrOut
from app.modules.receipts.service import ReceiptService

router = APIRouter(prefix="/receipts", tags=["小票 OCR"])


def get_service() -> ReceiptService:
    return ReceiptService()


@router.post("/ocr", response_model=ReceiptOcrOut, summary="小票 OCR 识别")
def ocr_receipt(
    file: Annotated[UploadFile, File(..., description="小票图片 jpg/jpeg/png/webp，≤10MB")],
    service: Annotated[ReceiptService, Depends(get_service)],
):
    """上传小票图片，识别并拆成待确认账目；确认入库走新增账目接口。"""
    content = file.file.read()
    return service.recognize(content, file.filename or "receipt.jpg")
