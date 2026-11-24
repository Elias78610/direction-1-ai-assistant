from collections.abc import Generator
from datetime import datetime
from sqlalchemy import create_engine,DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)
#数据库session会话的链接工厂
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键id")
    created_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="创建时间")
    updated_time: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

#向外提供数据库会话
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
