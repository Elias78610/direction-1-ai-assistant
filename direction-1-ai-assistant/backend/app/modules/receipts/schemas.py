"""小票 OCR 响应契约（对应接口契约 4.4）。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.params import NaiveDatetime


class ReceiptItemOut(BaseModel):
    """从小票拆出的一笔待确认账目。"""

    amount: str | None = Field(None, description="金额，元两位小数；识别不出为 null")
    category: str | None = Field(None, description="消费类别；识别不出为 null，交前端兜底")
    spent_at: NaiveDatetime | None = Field(None, description="小票时间；识别不出为 null")
    note: str | None = Field(None, description="商品名 / 商户备注")
    source: Literal["ocr"] = "ocr"
    confidence: float = Field(..., ge=0, le=1)


class ReceiptOcrOut(BaseModel):
    """OCR 识别结果；每笔都需用户确认后再入库。"""

    image_path: str = Field(..., description="小票图片在 data/uploads/ 下的相对路径")
    raw_text: str = Field(..., description="OCR 原始识别文本")
    items: list[ReceiptItemOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, description="低置信度或字段缺失提示")
