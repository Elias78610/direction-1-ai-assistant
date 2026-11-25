"""测试环境：用 SQLite 内存库替代 MySQL，避免污染开发数据。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

# 内存库 + StaticPool：所有请求共享同一个 SQLite 连接
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_database():
    """每个用例前重建表，保证用例之间互不影响。"""
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    """直接访问测试库，用于断言没有产生脏数据。"""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def db_session_factory():
    """返回 session 工厂，用于模拟多个并发请求各自的数据库会话。"""
    return TestSession
