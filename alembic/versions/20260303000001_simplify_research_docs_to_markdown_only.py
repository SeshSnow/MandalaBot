"""Simplify research_documents to markdown-only storage

Remove content_json column and make content_markdown required.
This simplifies the storage model by storing markdown directly
from the agent instead of JSON + renderer.

Revision ID: 20260303000001
Revises: 20260217000001
Create Date: 2026-03-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260303000001"
down_revision: str | None = "20260217000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # First, update any NULL content_markdown rows to have a placeholder
    # This is needed before we can make the column NOT NULL
    op.execute(
        """
        UPDATE research_documents
        SET content_markdown = '# Document content not available'
        WHERE content_markdown IS NULL
        """
    )

    # Make content_markdown NOT NULL
    op.alter_column(
        "research_documents",
        "content_markdown",
        existing_type=sa.Text(),
        nullable=False,
    )

    # Drop the content_json column
    op.drop_column("research_documents", "content_json")


def downgrade() -> None:
    # Re-add the content_json column
    op.add_column(
        "research_documents",
        sa.Column("content_json", postgresql.JSON(), nullable=True),
    )

    # Set a default empty JSON for existing rows
    op.execute(
        """
        UPDATE research_documents
        SET content_json = '{}'::jsonb
        """
    )

    # Make content_json NOT NULL
    op.alter_column(
        "research_documents",
        "content_json",
        existing_type=postgresql.JSON(),
        nullable=False,
    )

    # Make content_markdown nullable again
    op.alter_column(
        "research_documents",
        "content_markdown",
        existing_type=sa.Text(),
        nullable=True,
    )
