"""
Module-level DB session factory — initialized at server startup.

Tools and services import from here to get DB sessions without needing
direct access to app.state. The factory is set once during lifespan startup.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_factory: "async_sessionmaker[AsyncSession] | None" = None


def init(factory: "async_sessionmaker[AsyncSession]") -> None:
    """Initialize the module-level session factory. Called once at startup."""
    global _factory
    _factory = factory


def async_session_factory():
    """
    Return a new async session context manager.

    Usage: async with async_session_factory() as session: ...
    """
    if _factory is None:
        raise RuntimeError("DB session factory not initialized. Ensure Mandala DB is configured.")
    return _factory()


@asynccontextmanager
async def get_db_context():
    """
    Async context manager yielding a committed/rolled-back AsyncSession.

    Usage: async with get_db_context() as session: ...
    """
    if _factory is None:
        raise RuntimeError("DB session factory not initialized. Ensure Mandala DB is configured.")
    async with _factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
