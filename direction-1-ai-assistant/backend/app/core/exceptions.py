"""统一异常定义与全局异常处理器。"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)

# HTTP 状态码到业务错误码的映射，保持前端收到的 code 稳定
HTTP_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


class AppException(Exception):
    """业务异常基类：业务层只描述错误，不关心 HTTP 细节。"""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


class NotFoundError(AppException):
    """资源不存在。"""

    def __init__(self, message: str = "资源不存在", code: str = "NOT_FOUND"):
        super().__init__(code=code, message=message, status_code=404)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """构造统一错误响应，附带当前请求 ID。"""
    content: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_var.get(),
    }
    if errors:
        content["errors"] = errors
    return JSONResponse(status_code=status_code, content=content)


async def _handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message)


async def _handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """把 FastAPI / Starlette 的 HTTPException 也转换成统一结构。"""
    code = HTTP_CODE_MAP.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "请求失败"
    return _error_response(exc.status_code, code, message)


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """参数校验错误：保留字段位置和原因，方便前端定位。"""
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return _error_response(422, "VALIDATION_ERROR", "参数校验失败", errors)


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """未知异常：堆栈写日志，响应只给通用提示。"""
    logger.exception("未处理的异常: %s", exc)
    return _error_response(500, "INTERNAL_ERROR", "服务器内部错误，请稍后重试")


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器，保证所有接口错误格式一致。"""
    app.add_exception_handler(AppException, _handle_app_exception)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected)
