from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = {"comment": "账目表"}

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, comment="金额，单位：元")
    category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="消费类别")
    spent_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="消费时间")
    note: Mapped[str | None] = mapped_column(
        String(255), comment="备注")
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
        comment="来源：manual 手动 / nlp 自然语言 / ocr 小票识别")
    raw_text: Mapped[str | None] = mapped_column(
        Text, comment="原始输入文本或 OCR 识别内容")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True,
        comment="所属用户，登录功能未启用时可为空")
