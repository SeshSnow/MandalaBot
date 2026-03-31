"""Storage backend interface and implementations.

Provides an abstraction layer for workspace file access, enabling both
local filesystem and remote (S3/GCS) storage with the same interface.
"""

from nanobot.storage.base import StorageBackend
from nanobot.storage.local import LocalBackend
from nanobot.storage.factory import create_storage

__all__ = ["StorageBackend", "LocalBackend", "create_storage"]
