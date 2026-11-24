from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Expense(Base):
    """账目表。

    金额使用 Decimal 存储避免浮点误差；删除为硬删除，记录直接移除。
    """

    __tablename__ = "expenses"
    __table_args__ = {"comment": "账目表"}

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="金额，单位：元，最多两位小数")
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="消费类别，取值见 constants.CATEGORIES")
    spent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="消费发生时间")
    note: Mapped[str | None] = mapped_column(
        String(255), comment="备注，用户手动填写")
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
        comment="录入来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: Mapped[str | None] = mapped_column(
        Text, comment="原始输入文本：自然语言记账的原句或 OCR 识别内容")
    image_path: Mapped[str | None] = mapped_column(
        String(255), comment="小票或截图文件路径，OCR 录入时保存")
