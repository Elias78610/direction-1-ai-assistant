from app.db.session import Base
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    username: Mapped[str] = mapped_column(String(50),comment="账号",nullable=False)
    password: Mapped[str] = mapped_column(String(100),comment="密码",nullable=False)
    name: Mapped[str] = mapped_column(String(50),comment="姓名",nullable=False    )

