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
        config: Storage config dict with 'type' key ('local' or 'azure').
            If None, falls back to workspace path (local mode).
        workspace: Workspace path for local mode (fallback if no config).
        tenant_id: Tenant ID for multi-tenant prefix scoping.

    Returns:
        StorageBackend instance.

    Examples:
        # Local development
        storage = create_storage(workspace="/path/to/workspace")

        # Azure Blob Storage production
        storage = create_storage(config={
            "type": "azure",
            "azure": {
                "connection_string": "DefaultEndpointsProtocol=...",
                "container": "nanobot-workspace",
                "prefix": "workspaces/{tenant_id}/"
            }
        }, tenant_id="tenant_123")
    """
    if config and config.get("type") == "azure":
        azure_config = config.get("azure", {})
        prefix = azure_config.get("prefix", "")
        if tenant_id and "{tenant_id}" in prefix:
            prefix = prefix.replace("{tenant_id}", tenant_id)

        from nanobot.storage.azure import AzureBackend
        return AzureBackend(
            connection_string=azure_config["connection_string"],
            container=azure_config.get("container", "nanobot-workspace"),
            prefix=prefix,
        )

    # Default: local filesystem
    root = str(workspace) if workspace else "."
    return LocalBackend(root=root)
