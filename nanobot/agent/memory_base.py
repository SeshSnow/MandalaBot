"""
MemoryBackend protocol and factory.

The existing MemoryStore (filesystem) satisfies this protocol.
A DB-backed implementation can be swapped in when Mandala is enabled.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol for long-term memory persistence backends."""

    def read_long_term(self) -> str:
        """Return the current long-term memory content."""
        ...

    def write_long_term(self, content: str) -> None:
        """Overwrite the long-term memory with new content."""
        ...

    def append_history(self, entry: str) -> None:
        """Append a timestamped entry to the history log."""
        ...

    def get_memory_context(self) -> str:
        """Return formatted memory context for inclusion in the system prompt."""
        ...


def create_memory_store(config, workspace) -> "MemoryBackend":
    """
    Factory: return the appropriate MemoryBackend.

    Falls back to the filesystem MemoryStore when Mandala DB is not configured.
    (DB-backed memory is left as a future extension point.)

    Args:
        config: MandalaConfig instance (or None).
        workspace: Path to the local workspace directory.
    """
    from nanobot.agent.memory import MemoryStore
    return MemoryStore(workspace)
