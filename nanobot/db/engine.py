"""
Async SQLAlchemy engine and session factory for Mandala.

All DB work goes through the engine/session factory created here.
Only constructed when Mandala is enabled (database_url configured).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine from a database URL."""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to the given engine."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def make_get_db(session_factory: async_sessionmaker[AsyncSession]):
    """Return a FastAPI dependency that yields an AsyncSession."""

    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    return get_db


def make_get_db_context(session_factory: async_sessionmaker[AsyncSession]):
    """Return a context manager that yields an AsyncSession (for non-FastAPI use)."""

    @asynccontextmanager
    async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return get_db_context
