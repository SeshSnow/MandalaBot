"""Hybrid vector + full-text search store (pgvector + tsvector)."""

import uuid

from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from nanobot.db.base import Base, TimestampMixin

try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False
    Vector = None


class NanobotVectorStore(Base, TimestampMixin):
    __tablename__ = "nanobot_vector_store"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("uuid_generate_v4()"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"),
    )
    # Vector column — only if pgvector is installed
    embedding = mapped_column(Vector(2000) if _VECTOR_AVAILABLE else Text, nullable=True)
    fts_tokens = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        Index(
            "ix_nanobot_vector_store_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_nanobot_vector_store_fts_gin",
            "fts_tokens",
            postgresql_using="gin",
        ),
    )
