"""请求上下文中间件：生成请求 ID，记录访问日志和耗时。"""

import logging
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """给每个请求分配 ID，并记录方法、路径、状态码和耗时。"""

    async def dispatch(self, request: Request, call_next):
        # 前端可携带 X-Request-ID 串联日志；没有则由服务端生成
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # 兜底未处理异常：响应给前端通用提示，完整堆栈只写日志
            logger.exception("请求处理失败 %s %s", request.method, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误，请稍后重试",
                    "request_id": request_id,
                },
            )
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "%s %s -> %s %.1fms",
                request.method, request.url.path, status_code, elapsed_ms,
            )
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
