"""
Alembic environment configuration for MandalaBot.

Reads database URL from DATABASE_URL env var.
Run from the MandalaBot repo root: alembic upgrade head
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

import nanobot.db.models  # noqa: F401 - registers all models on Base.metadata
from alembic import context
from nanobot.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_sync_url() -> str:
    """Return a sync (psycopg2) DB URL for Alembic."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        # Fallback: try legacy env var used by Mandala
        url = os.getenv("DATABASE_URL", "")
    if not url:
        return "postgresql://nanobot:nanobot@localhost:5432/nanobot"
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conf = config.get_section(config.config_ini_section) or {}
    conf["sqlalchemy.url"] = _get_sync_url()
    connectable = engine_from_config(
        conf, prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
