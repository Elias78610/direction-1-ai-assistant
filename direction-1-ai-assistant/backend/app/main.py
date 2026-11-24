from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import router as api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import Base, engine
from app.modules import Expense  # noqa: F401  导入模型以注册表结构

setup_logging(settings.log_level)

Base.metadata.create_all(engine)


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 最后添加的中间件位于最外层，保证每个请求（含 CORS 预检）都有请求 ID 和访问日志
app.add_middleware(RequestContextMiddleware)

register_exception_handlers(app)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok", "db": db_status}
