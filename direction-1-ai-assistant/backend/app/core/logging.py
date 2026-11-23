"""日志配置：统一输出格式，并自动带上当前请求 ID。"""

import logging
import sys
from contextvars import ContextVar

# 当前请求的 ID：中间件写入，日志过滤器读取，未处于请求中时为 "-"
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """把当前请求 ID 写入日志记录，方便按请求排查。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """初始化根日志：输出到控制台，格式包含时间、级别、模块和请求 ID。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # uvicorn 自带日志改为统一格式；访问日志由请求中间件记录，避免重复
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
