"""Local filesystem storage backend.

Wraps pathlib operations behind the StorageBackend interface.
Used for development and single-machine deployments.
"""

from __future__ import annotations

from pathlib import Path

from nanobot.storage.base import StorageBackend


class LocalBackend(StorageBackend):
    """Local filesystem storage — wraps pathlib."""

    def __init__(self, root: str | Path, allowed_prefix: str = ""):
        root_str = str(root) if isinstance(root, Path) else root
        super().__init__(root=root_str, allowed_prefix=allowed_prefix)
        self._root_path = Path(self.root).expanduser().resolve()

    def _to_path(self, resolved: str) -> Path:
        """Convert resolved string path to Path object."""
        # Strip root prefix to get relative path
        if self.root and resolved.startswith(self.root):
            relative = resolved[len(self.root):].lstrip("/")
            return self._root_path / relative if relative else self._root_path
        return Path(resolved)

    async def _read(self, resolved_path: str) -> str:
        fp = self._to_path(resolved_path)
        if not fp.exists():
            raise FileNotFoundError(f"File not found: {resolved_path}")
        if fp.is_dir():
            raise IsADirectoryError(f"Is a directory: {resolved_path}")
        return fp.read_text(encoding="utf-8")

    async def _write(self, resolved_path: str, content: str) -> None:
        fp = self._to_path(resolved_path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    async def _list(self, resolved_path: str) -> list[str]:
        dp = self._to_path(resolved_path)
        if not dp.exists():
            raise FileNotFoundError(f"Directory not found: {resolved_path}")
        if not dp.is_dir():
            raise NotADirectoryError(f"Not a directory: {resolved_path}")
        return sorted(
            item.name for item in dp.iterdir()
            if not item.name.startswith(".")
        )

    async def _exists(self, resolved_path: str) -> bool:
        return self._to_path(resolved_path).exists()

    async def _is_dir(self, resolved_path: str) -> bool:
        return self._to_path(resolved_path).is_dir()

    async def delete(self, path: str) -> None:
        resolved = self._resolve(path)
        fp = self._to_path(resolved)
        if fp.is_dir():
            import shutil
            shutil.rmtree(fp)
        elif fp.exists():
            fp.unlink()
