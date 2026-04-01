"""
SessionStore protocol — the interface both FileSessionManager and DBSessionManager satisfy.

The existing SessionManager (filesystem) already satisfies this protocol.
DBSessionManager implements the same interface backed by PostgreSQL.
"""

from typing import Any, Protocol, runtime_checkable

from nanobot.session.manager import Session


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for conversation session persistence backends."""

    def get_or_create(self, key: str) -> Session:
        """Return existing session or create a new one."""
        ...

    def save(self, session: Session) -> None:
        """Persist the session."""
        ...

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return metadata for all sessions."""
        ...

    def invalidate(self, key: str) -> None:
        """Remove a session from cache (and optionally from storage)."""
        ...


def create_session_manager(config, workspace) -> "SessionStore":
    """
    Factory: return a DBSessionManager when Mandala DB is configured,
    otherwise fall back to the filesystem SessionManager.

    Args:
        config: MandalaConfig instance (or None).
        workspace: Path to the local workspace directory.
    """
    from nanobot.session.manager import SessionManager

    if config is not None and getattr(config, "enabled", False):
        try:
            from nanobot.session.db_manager import DBSessionManager
            return DBSessionManager(config)
        except ImportError:
            pass

    return SessionManager(workspace)
