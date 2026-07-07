"""
应用异常体系

提供统一的异常类和错误码枚举，确保所有 API 错误返回一致的 JSON 结构。

三层结构:
  AppException (HTTPException 基类)
   ├── NotFoundException       (404)
   ├── ValidationException     (422)
   ├── FileException           (400)
   ├── AgentException          (500)
   └── DatabaseException       (500)

用法:
    from app.core.exceptions import (
        NotFoundException, ValidationException,
        FileException, AgentException,
    )

    # 在 Service/API 中直接抛
    raise NotFoundException("数据集", dataset_id=42)
    raise ValidationException("文件格式不支持")
    raise FileException("文件过大", code=ErrorCode.FILE_TOO_LARGE)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# Python 3.11+ 兼容：HTTP_422 → HTTP_422_UNPROCESSABLE_CONTENT
try:
    HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT
except AttributeError:
    HTTP_422 = status.HTTP_422  # fallback 旧版本


# ──────────────────────────────────────────────
#  错误码枚举
# ──────────────────────────────────────────────
class ErrorCode(str, Enum):
    """应用级错误码，每个码对应一类错误场景。"""

    # ── 通用 ──
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # ── 文件 ──
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_PARSE_ERROR = "FILE_PARSE_ERROR"
    FILE_MISSING = "FILE_MISSING"

    # ── Agent ──
    AGENT_EXECUTION_ERROR = "AGENT_EXECUTION_ERROR"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_OUTPUT_INVALID = "AGENT_OUTPUT_INVALID"

    # ── 数据 ──
    DATABASE_ERROR = "DATABASE_ERROR"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"

    # ── 外部服务 ──
    LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"


# ──────────────────────────────────────────────
#  统一错误响应体
# ──────────────────────────────────────────────
class ErrorResponse:
    """构造统一的错误响应字典。"""

    @staticmethod
    def create(
        code: ErrorCode,
        message: str,
        details: Any = None,
    ) -> dict:
        return {
            "success": False,
            "error": {
                "code": code.value,
                "message": message,
                "details": details,
            },
        }


# ──────────────────────────────────────────────
#  异常基类
# ──────────────────────────────────────────────
class AppException(HTTPException):
    """
    应用异常基类。

    所有业务异常继承此类，通过 error_code 区分错误类型，
    响应体始终为统一的 ErrorResponse 格式。
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        self.error_code = error_code
        self.details = details
        super().__init__(
            status_code=status_code,
            detail=ErrorResponse.create(error_code, message, details),
        )


# ──────────────────────────────────────────────
#  具体异常类
# ──────────────────────────────────────────────
class NotFoundException(AppException):
    """资源不存在（404）。"""

    def __init__(
        self,
        resource: str = "资源",
        identifier: Any = None,
        details: Any = None,
    ) -> None:
        message = f"{resource}不存在"
        if identifier is not None:
            message += f"（标识：{identifier}）"
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationException(AppException):
    """参数校验失败（422）。"""

    def __init__(
        self,
        message: str = "请求参数校验失败",
        details: Any = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=HTTP_422,
            details=details,
        )


class FileException(AppException):
    """文件操作相关错误（400）。"""

    def __init__(
        self,
        message: str = "文件处理失败",
        code: ErrorCode = ErrorCode.FILE_PARSE_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(
            error_code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class AgentException(AppException):
    """Agent 执行相关错误（500）。"""

    def __init__(
        self,
        message: str = "Agent 执行失败",
        code: ErrorCode = ErrorCode.AGENT_EXECUTION_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(
            error_code=code,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class DatabaseException(AppException):
    """数据库操作相关错误（500）。"""

    def __init__(
        self,
        message: str = "数据库操作失败",
        details: Any = None,
    ) -> None:
        super().__init__(
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


# ──────────────────────────────────────────────
#  全局异常处理器（注册到 FastAPI app）
# ──────────────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:
    """
    在 FastAPI 应用中注册统一异常处理器。

    应在应用启动阶段调用:
        app = FastAPI()
        register_exception_handlers(app)
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: FastAPI.request_class,  # type: ignore[arg-type]
        exc: AppException,
    ) -> JSONResponse:
        """捕获所有 AppException 子类，返回统一 JSON 错误响应。"""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,  # 构造时已是 ErrorResponse 格式
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: FastAPI.request_class,  # type: ignore[arg-type]
        exc: RequestValidationError,
    ) -> JSONResponse:
        """捕获 FastAPI 内置的 Pydantic 校验错误，转为统一格式。"""
        return JSONResponse(
            status_code=HTTP_422,
            content=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message="请求参数校验失败",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: FastAPI.request_class,  # type: ignore[arg-type]
        exc: Exception,
    ) -> JSONResponse:
        """兜底：捕获所有未处理的异常，返回 500 + 统一格式。"""
        # 生产环境不暴露原始异常信息
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.create(
                code=ErrorCode.INTERNAL_ERROR,
                message="服务器内部错误" if not app.debug else str(exc),
                details=None if not app.debug else str(exc),
            ),
        )
