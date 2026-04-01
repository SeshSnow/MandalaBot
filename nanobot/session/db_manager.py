"""
DB-backed SessionManager.

Stores sessions in PostgreSQL (conversations + messages tables created by
alembic migration 20260204000001) instead of JSONL files on the filesystem.

Session keys are tenant-scoped: "{tenant}:{channel}:{chat_id}" or "{channel}:{chat_id}".
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger

from nanobot.session.manager import Session


class DBSessionManager:
    """
    Session manager backed by PostgreSQL.

    Uses a sync-compatible API (same as filesystem SessionManager) by running
    async DB operations in a dedicated event loop via asyncio.run_coroutine_threadsafe
    or, when already inside an event loop, scheduling them as tasks.

    In practice the agent loop is always async so we use asyncio directly.
    """

    def __init__(self, mandala_config) -> None:
        from nanobot.db.engine import create_engine, create_session_factory, make_get_db_context
        engine = create_engine(mandala_config.async_database_url)
        self._session_factory = create_session_factory(engine)
        self._get_db_context = make_get_db_context(self._session_factory)
        self._cache: dict[str, Session] = {}

    # ------------------------------------------------------------------
    # Public interface (mirrors SessionManager)
    # ------------------------------------------------------------------

    def get_or_create(self, key: str) -> Session:
        if key in self._cache:
            return self._cache[key]
        session = self._run_async(self._load_async(key))
        if session is None:
            session = Session(key=key)
        self._cache[key] = session
        return session

    def save(self, session: Session) -> None:
        self._cache[session.key] = session
        self._run_async(self._save_async(session))

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._run_async(self._list_async())

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------

    async def _load_async(self, key: str) -> Session | None:
        from sqlalchemy import select, text
        async with self._get_db_context() as db:
            # conversations table stores key as id
            result = await db.execute(
                text("SELECT id, title, created_at, updated_at FROM conversations WHERE id = :key"),
                {"key": key},
            )
            row = result.fetchone()
            if row is None:
                return None

            msgs_result = await db.execute(
                text(
                    "SELECT role, content, tool_calls, tool_call_id, created_at "
                    "FROM messages WHERE conversation_id = :key ORDER BY created_at ASC"
                ),
                {"key": key},
            )
            messages = []
            for m in msgs_result.fetchall():
                entry: dict[str, Any] = {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.created_at.isoformat() if m.created_at else "",
                }
                if m.tool_calls:
                    entry["tool_calls"] = m.tool_calls
                if m.tool_call_id:
                    entry["tool_call_id"] = m.tool_call_id
                messages.append(entry)

            session = Session(
                key=key,
                messages=messages,
                created_at=row.created_at or datetime.now(),
                updated_at=row.updated_at or datetime.now(),
            )
            return session

    async def _save_async(self, session: Session) -> None:
        from sqlalchemy import text
        async with self._get_db_context() as db:
            # Upsert conversation row
            await db.execute(
                text(
                    "INSERT INTO conversations (id, title, created_at, updated_at) "
                    "VALUES (:id, :title, :created_at, :updated_at) "
                    "ON CONFLICT (id) DO UPDATE SET updated_at = EXCLUDED.updated_at"
                ),
                {
                    "id": session.key,
                    "title": None,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                },
            )

            # Determine which messages are new (not yet persisted)
            count_result = await db.execute(
                text("SELECT COUNT(*) FROM messages WHERE conversation_id = :key"),
                {"key": session.key},
            )
            persisted_count = count_result.scalar() or 0
            new_messages = session.messages[persisted_count:]

            for msg in new_messages:
                from uuid import uuid4
                tool_calls = msg.get("tool_calls")
                await db.execute(
                    text(
                        "INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_call_id, created_at, updated_at) "
                        "VALUES (:id, :conv_id, :role, :content, :tool_calls, :tool_call_id, now(), now())"
                    ),
                    {
                        "id": uuid4().hex,
                        "conv_id": session.key,
                        "role": msg.get("role", "user"),
                        "content": msg.get("content") or "",
                        "tool_calls": json.dumps(tool_calls) if tool_calls else None,
                        "tool_call_id": msg.get("tool_call_id"),
                    },
                )

    async def _list_async(self) -> list[dict[str, Any]]:
        from sqlalchemy import text
        async with self._get_db_context() as db:
            result = await db.execute(
                text("SELECT id, created_at, updated_at FROM conversations ORDER BY updated_at DESC")
            )
            return [
                {"key": row.id, "created_at": str(row.created_at), "updated_at": str(row.updated_at)}
                for row in result.fetchall()
            ]

    # ------------------------------------------------------------------
    # Event loop bridge
    # ------------------------------------------------------------------

    @staticmethod
    def _run_async(coro):
        """Run a coroutine, handling both in-loop and out-of-loop contexts."""
        try:
            loop = asyncio.get_running_loop()
            # Already inside an event loop — schedule as a task and wait
            import concurrent.futures
            fut = asyncio.run_coroutine_threadsafe(coro, loop)
            return fut.result(timeout=30)
        except RuntimeError:
            # No running loop — use asyncio.run
            return asyncio.run(coro)
