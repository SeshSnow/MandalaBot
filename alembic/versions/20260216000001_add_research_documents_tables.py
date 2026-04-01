"""Add research_documents and research_executions tables

Revision ID: 20260216000001
Revises: 20260204000001
Create Date: 2026-02-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260216000001"
down_revision: str | None = "20260204000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types first
    research_type_enum = postgresql.ENUM(
        "market_research",
        "customer_avatar",
        "competitor_analysis",
        "sales_avatar_extension",
        "offer_brief",
        "necessary_beliefs",
        name="research_type_enum",
        create_type=True,
    )
    research_type_enum.create(op.get_bind(), checkfirst=True)

    execution_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="execution_status_enum",
        create_type=True,
    )
    execution_status_enum.create(op.get_bind(), checkfirst=True)

    # Create research_documents table
    op.create_table(
        "research_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shopify_store_id", sa.String(255), nullable=False, index=True),
        sa.Column("product_id", sa.String(255), nullable=True, index=True),
        sa.Column(
            "document_type",
            postgresql.ENUM(
                "market_research",
                "customer_avatar",
                "competitor_analysis",
                "sales_avatar_extension",
                "offer_brief",
                "necessary_beliefs",
                name="research_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content_json", postgresql.JSON(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("azure_blob_url", sa.String(500), nullable=True),
        sa.Column("vector_store_file_id", sa.String(100), nullable=True),
        sa.Column("schema_version", sa.String(20), nullable=False, default="1.0.0"),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), default=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "parent_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Create indexes for common query patterns
    op.create_index(
        "ix_research_documents_store_type_active",
        "research_documents",
        ["shopify_store_id", "document_type", "active"],
    )

    # Create research_executions table
    op.create_table(
        "research_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shopify_store_id", sa.String(255), nullable=False, index=True),
        sa.Column(
            "research_type",
            postgresql.ENUM(
                "market_research",
                "customer_avatar",
                "competitor_analysis",
                "sales_avatar_extension",
                "offer_brief",
                "necessary_beliefs",
                name="research_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "running",
                "completed",
                "failed",
                name="execution_status_enum",
                create_type=False,
            ),
            nullable=False,
            default="pending",
        ),
        sa.Column("input_params", postgresql.JSON(), nullable=True),
        sa.Column(
            "result_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("research_executions")
    op.drop_index("ix_research_documents_store_type_active", table_name="research_documents")
    op.drop_table("research_documents")

    # Drop enum types
    execution_status_enum = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="execution_status_enum",
    )
    execution_status_enum.drop(op.get_bind(), checkfirst=True)

    research_type_enum = postgresql.ENUM(
        "market_research",
        "customer_avatar",
        "competitor_analysis",
        "sales_avatar_extension",
        "offer_brief",
        "necessary_beliefs",
        name="research_type_enum",
    )
    research_type_enum.drop(op.get_bind(), checkfirst=True)
