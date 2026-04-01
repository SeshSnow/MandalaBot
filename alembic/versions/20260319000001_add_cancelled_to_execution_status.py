"""Add cancelled status to execution_status_enum

Revision ID: 20260319000001
Revises: 20260303000001
Create Date: 2026-03-19

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260319000001"
down_revision: str | None = "20260303000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add 'CANCELLED' value to execution_status_enum
    # Note: SQLAlchemy's Enum column type uses the enum member name (uppercase),
    # not the enum value (lowercase), so we need to add the uppercase version
    op.execute("ALTER TYPE execution_status_enum ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums
    # This is a one-way migration - to downgrade, you'd need to:
    # 1. Convert the column to text
    # 2. Drop and recreate the enum without 'cancelled'
    # 3. Convert the column back to the enum
    # This is complex and potentially destructive, so we skip it
    pass
