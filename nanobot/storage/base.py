"""Abstract storage backend interface.

All workspace file access goes through this interface. Implementations
exist for local filesystem, S3, and GCS. The agent never touches
pathlib.Path directly — it always goes through StorageBackend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Any


class StorageBackend(ABC):
    """
    Abstract storage interface for workspace file operations.

    All paths are relative to the backend's root. The backend handles:
    - Path resolution (relative → absolute)
    - Permission enforcement (allowed prefixes)
    - Directory creation (on write)
    - Tenant isolation (via prefix)
    """

    def __init__(self, root: str = "", allowed_prefix: str = ""):
        """
        Args:
            root: Base path/prefix for all operations.
            allowed_prefix: If set, all paths must start with this prefix.
        """
        self.root = root.rstrip("/")
        self.allowed_prefix = allowed_prefix.rstrip("/") if allowed_prefix else ""

    def _resolve(self, path: str) -> str:
        """Resolve a relative path against root and validate permissions."""
        # Normalize path
        path = path.strip("/")

        # Resolve relative paths against root
        if self.root:
            resolved = f"{self.root}/{path}" if path else self.root
        else:
            resolved = path

        # Clean up double slashes and ./
        resolved = str(PurePosixPath(resolved))

        # Permission check
        if self.allowed_prefix and not resolved.startswith(self.allowed_prefix):
            raise PermissionError(
                f"Path '{path}' resolves to '{resolved}' which is outside "
                f"allowed prefix '{self.allowed_prefix}'"
            )

        return resolved

    @abstractmethod
    async def _read(self, resolved_path: str) -> str:
        """Implementation-specific read. Receives already-resolved path."""
        ...

    @abstractmethod
    async def _write(self, resolved_path: str, content: str) -> None:
        """Implementation-specific write. Receives already-resolved path."""
        ...

    @abstractmethod
    async def _list(self, resolved_path: str) -> list[str]:
        """Implementation-specific list. Receives already-resolved path."""
        ...

    @abstractmethod
    async def _exists(self, resolved_path: str) -> bool:
        """Implementation-specific exists. Receives already-resolved path."""
        ...

    @abstractmethod
    async def _is_dir(self, resolved_path: str) -> bool:
        """Implementation-specific is_dir. Receives already-resolved path."""
        ...

    # ── Public API (resolves paths, enforces permissions) ──────────

    async def read(self, path: str) -> str:
        """Read file contents as UTF-8 text."""
        resolved = self._resolve(path)
        return await self._read(resolved)

    async def read_bytes(self, path: str) -> bytes:
        """Read file contents as raw bytes. Override for binary support."""
        return (await self.read(path)).encode("utf-8")

    async def write(self, path: str, content: str) -> None:
        """Write text content to a file. Creates parent directories."""
        resolved = self._resolve(path)
        await self._write(resolved, content)

    async def write_bytes(self, path: str, content: bytes) -> None:
        """Write raw bytes to a file. Override for binary support."""
        await self.write(path, content.decode("utf-8"))

    async def list(self, path: str) -> list[str]:
        """List directory contents. Returns entry names (not full paths)."""
        resolved = self._resolve(path)
        return await self._list(resolved)

    async def exists(self, path: str) -> bool:
        """Check if a path exists."""
        resolved = self._resolve(path)
        return await self._exists(resolved)

    async def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        resolved = self._resolve(path)
        return await self._is_dir(resolved)

    async def delete(self, path: str) -> None:
        """Delete a file. Override for backend-specific behavior."""
        raise NotImplementedError(f"{self.__class__.__name__} does not support delete")
