"""Add nanobot_vector_store table with pgvector and full-text search

Revision ID: 20260217000001
Revises: 20260216000001
Create Date: 2026-02-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "20260217000001"
down_revision: str | None = "20260216000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create nanobot_vector_store with HNSW and GIN indexes."""
    # Enable required extensions (idempotent)
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "nanobot_vector_store",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("embedding", Vector(2000), nullable=True),
        sa.Column(
            "fts_tokens",
            sa.dialects.postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # HNSW index for fast approximate nearest-neighbor vector search
    op.execute(
        """
        CREATE INDEX ix_nanobot_vector_store_embedding_hnsw
        ON nanobot_vector_store
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # GIN index for fast full-text keyword search
    op.create_index(
        "ix_nanobot_vector_store_fts_gin",
        "nanobot_vector_store",
        ["fts_tokens"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop nanobot_vector_store and its indexes."""
    op.drop_index(
        "ix_nanobot_vector_store_fts_gin",
        table_name="nanobot_vector_store",
    )
    op.drop_index(
        "ix_nanobot_vector_store_embedding_hnsw",
        table_name="nanobot_vector_store",
    )
    op.drop_table("nanobot_vector_store")
    # Extensions left in place intentionally (shared across tables)
