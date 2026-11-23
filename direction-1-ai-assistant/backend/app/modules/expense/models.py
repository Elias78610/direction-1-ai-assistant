from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Expense(Base):
    """账目表。

    金额使用 Decimal 存储避免浮点误差；删除采用软删除标记，
    后续查询默认只返回 is_deleted = 0 的记录。
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
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false(),
        index=True, comment="是否已删除：0 未删除，1 已删除（软删除标记）")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True,
        comment="所属用户 ID，登录功能未启用时为空")
