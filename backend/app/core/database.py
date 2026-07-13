"""
数据库引擎模块

基于 SQLAlchemy 2.0 async 风格，提供异步引擎、Session 工厂、FastAPI 依赖注入。

用法:
    from app.core.database import get_db, async_session, engine, check_db_health

    # FastAPI 依赖注入
    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Dataset))
        return result.scalars().all()

    # 非请求上下文直接用工厂
    async with async_session() as db:
        result = await db.execute(select(Dataset))
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ──────────────────────────────────────────────
#  异步引擎（全局单例）
# ──────────────────────────────────────────────

engine = create_async_engine(
    settings.database.url,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    # 连接达到 pool_size + max_overflow 上限后，新请求等待的时间
    pool_timeout=30,
    # 连接空闲回收时间（-1 表示不禁用连接回收）
    pool_recycle=3600,
    # 使用前检查连接是否存活
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ──────────────────────────────────────────────
#  FastAPI 依赖注入
# ──────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Depends 用：每个请求获取一个独立的数据库会话。

    会话会在请求处理结束后自动关闭，确保连接归还到连接池。

    用法:
        @router.get("/api/v1/datasets")
        async def list_datasets(db: AsyncSession = Depends(get_db)):
            ...

    注: 如果 Service 层需要手动管理事务，Service 调用方通过此依赖获取 session。
    """
    async with async_session() as session:
        try:
            yield session
            # 请求正常结束时提交（由 Service 层控制，这里不自动提交）
        finally:
            await session.close()


# ──────────────────────────────────────────────
#  健康检查
# ──────────────────────────────────────────────

async def check_db_health() -> bool:
    """
    检查数据库连接是否正常。

    Returns:
        True 表示连接正常。
    """
    try:
        async with async_session() as session:
            await session.execute(  # type: ignore[call-overload]
                # SQLAlchemy 2.0: select(1) 替代 text("SELECT 1")
                __import__("sqlalchemy").text("SELECT 1")
            )
        return True
    except Exception:
        return False
