from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    """用户表。

    登录功能暂未启用，当前仅预留表结构；启用时应把 password
    改为哈希存储，并补充登录接口。
    """

    __tablename__ = "users"
    __table_args__ = {"comment": "用户表"}

    username: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="登录账号，唯一")
    password: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="登录密码，启用登录后改存哈希值")
    name: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="用户显示姓名")
