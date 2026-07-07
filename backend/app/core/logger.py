"""
应用日志系统

提供统一的日志工具，自动注入请求追踪 ID，支持开发/生产双模式。

用法:
    # 1. 在应用启动入口调用一次
    from app.core.logger import setup_logging
    setup_logging(level="INFO", use_json=False)

    # 2. 各模块获取 logger
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("数据加载完成", extra={"rows": 1000})
    # 输出: 2026-07-06 12:00:00 | INFO    | app.services.file | a1b2c3d4 | 数据加载完成 {"rows": 1000}

    # 3. 注册追踪中间件到 FastAPI
    from app.core.logger import TraceIDMiddleware
    app.add_middleware(TraceIDMiddleware)

模式:
  - 开发环境 (use_json=False): RichHandler 彩色输出
  - 生产环境 (use_json=True):  JSON 结构化日志，每行一个 JSON 对象
"""

from __future__ import annotations

import json
import logging
import logging.config
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

# ──────────────────────────────────────────────
#  请求追踪
# ──────────────────────────────────────────────

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
"""每个请求的追踪 ID，通过 ContextVar 在线程/协程间传递。"""


def get_trace_id() -> str:
    """获取当前上下文的 trace_id，无则返回空字符串。"""
    return trace_id_var.get()


def set_trace_id(trace_id: str | None = None) -> str:
    """
    设置当前上下文的 trace_id。

    Args:
        trace_id: 指定的 ID，为 None 时自动生成 8 位 hex。

    Returns:
        设置后的 trace_id。
    """
    tid = trace_id or uuid4().hex[:8]
    trace_id_var.set(tid)
    return tid


# ──────────────────────────────────────────────
#  Logger 获取
# ──────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    获取应用 logger。

    会自动将模块名映射为 ``app.<name>`` 命名空间，
    方便通过 logger 名称定位代码来源。

    Args:
        name: 模块的 __name__ 或自定义名称。

    Returns:
        已配置的 Logger 实例。
    """
    # 过滤掉 "app." 前缀的重叠
    if name.startswith("app."):
        logger_name = name
    elif name.startswith("backend."):
        logger_name = name.replace("backend.", "app.", 1)
    else:
        logger_name = f"app.{name}"
    return logging.getLogger(logger_name)


# ──────────────────────────────────────────────
#  日志过滤器：注入 trace_id
# ──────────────────────────────────────────────

class TraceIDFilter(logging.Filter):
    """自动将当前上下文的 trace_id 注入到每条日志记录的 ``record.trace_id`` 属性。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get() or "-"
        return True


# ──────────────────────────────────────────────
#  JSON 格式化器（生产环境）
# ──────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """
    输出 JSON 结构化的日志行，兼容 Logstash/Filebeat。

    每行输出:
    .. code-block:: json

        {
          "timestamp": "2026-07-06T12:00:00.000Z",
          "level": "INFO",
          "logger": "app.services.file",
          "trace_id": "a1b2c3d4",
          "message": "数据加载完成",
          "extra": {"rows": 1000}
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "message": record.getMessage(),
        }
        # 合并 extra 中自定义字段（不含标准 LogRecord 属性）
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry["extra"] = record.extra
        elif record.args:
            # record.args 中有结构化数据时也保留
            pass
        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ──────────────────────────────────────────────
#  日志初始化（应用启动入口调用一次）
# ──────────────────────────────────────────────

_is_initialized = False
"""防止重复初始化。"""


def setup_logging(level: str = "INFO", use_json: bool = False) -> None:
    """
    配置全局日志系统（应在应用启动时调用一次）。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）。
        use_json: True 输出 JSON 结构化日志；False 使用 Rich 彩色输出。
    """
    global _is_initialized
    if _is_initialized:
        return
    _is_initialized = True

    level_upper = level.upper()

    # 移除 root logger 的默认 handler，避免重复
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level_upper)

    # ── 创建 Handler ──
    if use_json:
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
    else:
        try:
            from rich.logging import RichHandler

            handler = RichHandler(
                show_time=True,
                show_path=False,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                omit_repeated_times=False,
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
        except ImportError:
            # Rich 未安装时降级为标准 Handler
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-7s | %(name)s | %(trace_id)s | %(message)s"
                )
            )

    handler.addFilter(TraceIDFilter())
    root.addHandler(handler)

    # 第三方库日志级别调整（抑制过多输出）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


# ──────────────────────────────────────────────
#  FastAPI 中间件：请求追踪
# ──────────────────────────────────────────────

class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 中间件。

    为每个请求生成/复用 trace_id，注入到 ContextVar 和响应头中。
    请求结束后清除 trace_id。

    用法:
        app = FastAPI()
        app.add_middleware(TraceIDMiddleware)
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Trace-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # 优先复用客户端传入的 trace_id，否则自动生成
        incoming_trace_id = request.headers.get(self.header_name)
        set_trace_id(incoming_trace_id)

        response = await call_next(request)

        # 将 trace_id 写入响应头
        response.headers[self.header_name] = get_trace_id()

        # 清除上下文，防止泄漏到下一个请求
        trace_id_var.set("")

        return response
