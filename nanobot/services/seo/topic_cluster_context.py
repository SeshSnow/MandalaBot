"""
Per-request context for topic cluster generation via the agent loop.
"""

from contextvars import ContextVar
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class TopicClusterRequestContext:
    """Request-scoped data for topic cluster generation."""

    __slots__ = ("brand_id", "db", "brand_context", "saved_cluster_id", "saved_cluster_structure")

    def __init__(self, brand_id: UUID, db: AsyncSession, brand_context: dict[str, Any]) -> None:
        self.brand_id = brand_id
        self.db = db
        self.brand_context = brand_context
        self.saved_cluster_id: str | None = None
        self.saved_cluster_structure: dict[str, Any] | None = None


_topic_cluster_context_var: ContextVar[TopicClusterRequestContext | None] = ContextVar(
    "topic_cluster_request_context", default=None,
)


def set_topic_cluster_request_context(brand_id: UUID, db: AsyncSession, brand_context: dict[str, Any]) -> None:
    _topic_cluster_context_var.set(TopicClusterRequestContext(brand_id=brand_id, db=db, brand_context=brand_context))


def get_topic_cluster_request_context() -> TopicClusterRequestContext | None:
    return _topic_cluster_context_var.get()


def clear_topic_cluster_request_context() -> None:
    _topic_cluster_context_var.set(None)
