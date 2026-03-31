"""Storage factory — creates the right backend from config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.storage.base import StorageBackend
from nanobot.storage.local import LocalBackend


def create_storage(
    config: dict[str, Any] | None = None,
    workspace: str | Path | None = None,
    tenant_id: str | None = None,
) -> StorageBackend:
    """
    Create a storage backend from config or workspace path.

    Args:
        config: Storage config dict with 'type' key ('local' or 's3').
            If None, falls back to workspace path (local mode).
        workspace: Workspace path for local mode (fallback if no config).
        tenant_id: Tenant ID for multi-tenant S3 prefix scoping.

    Returns:
        StorageBackend instance.

    Examples:
        # Local development
        storage = create_storage(workspace="/path/to/workspace")

        # S3 production
        storage = create_storage(config={
            "type": "s3",
            "s3": {
                "bucket": "mandala-prod",
                "prefix": "workspaces/{tenant_id}/",
                "region": "us-west-2"
            }
        }, tenant_id="tenant_123")
    """
    if config and config.get("type") == "s3":
        s3_config = config.get("s3", {})
        prefix = s3_config.get("prefix", "")
        if tenant_id and "{tenant_id}" in prefix:
            prefix = prefix.replace("{tenant_id}", tenant_id)

        from nanobot.storage.s3 import S3Backend
        return S3Backend(
            bucket=s3_config["bucket"],
            prefix=prefix,
            region=s3_config.get("region", "us-east-1"),
        )

    # Default: local filesystem
    root = str(workspace) if workspace else "."
    return LocalBackend(root=root)
