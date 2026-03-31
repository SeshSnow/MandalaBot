"""Azure Blob Storage backend.

Provides Azure Blob Storage-backed workspace storage for multi-tenant,
multi-machine deployments. Uses azure.storage.blob.aio for async operations.

Requires: pip install azure-storage-blob
"""

from __future__ import annotations

import logging
from typing import Any

from nanobot.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class AzureBackend(StorageBackend):
    """Azure Blob Storage backend."""

    def __init__(
        self,
        connection_string: str,
        container: str = "nanobot-workspace",
        prefix: str = "",
        allowed_prefix: str = "",
    ):
        super().__init__(root=prefix, allowed_prefix=allowed_prefix)
        self.connection_string = connection_string
        self.container = container
        self._client = None

    def _get_client(self):
        """Lazy-initialize Azure Blob Service client."""
        if self._client is None:
            try:
                from azure.storage.blob.aio import BlobServiceClient
                self._client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                logger.info("Azure Blob Storage client initialized")
            except ImportError as e:
                raise ImportError(
                    "azure-storage-blob is required for Azure storage. "
                    "Install with: pip install azure-storage-blob"
                ) from e
        return self._client

    def _to_blob_path(self, resolved_path: str) -> str:
        """Convert resolved path to Azure blob path."""
        return resolved_path.lstrip("/")

    def _get_container_client(self):
        return self._get_client().get_container_client(self.container)

    def _get_blob_client(self, blob_path: str):
        return self._get_client().get_blob_client(
            container=self.container,
            blob=blob_path,
        )

    async def _ensure_container(self) -> None:
        """Create container if it doesn't exist."""
        cc = self._get_container_client()
        if not await cc.exists():
            await cc.create_container()
            logger.info("Created Azure container: %s", self.container)

    async def _read(self, resolved_path: str) -> str:
        blob_path = self._to_blob_path(resolved_path)
        bc = self._get_blob_client(blob_path)

        try:
            from azure.core.exceptions import ResourceNotFoundError
        except ImportError:
            ResourceNotFoundError = Exception

        try:
            downloader = await bc.download_blob()
            data = await downloader.readall()
            return data.decode("utf-8")
        except ResourceNotFoundError:
            raise FileNotFoundError(f"File not found: {resolved_path}")
        except Exception as e:
            if "NotFound" in str(type(e).__name__) or "404" in str(e):
                raise FileNotFoundError(f"File not found: {resolved_path}")
            raise

    async def _write(self, resolved_path: str, content: str) -> None:
        await self._ensure_container()
        blob_path = self._to_blob_path(resolved_path)
        bc = self._get_blob_client(blob_path)

        from azure.storage.blob import ContentSettings
        await bc.upload_blob(
            data=content.encode("utf-8"),
            overwrite=True,
            content_settings=ContentSettings(content_type="text/plain; charset=utf-8"),
        )

    async def _list(self, resolved_path: str) -> list[str]:
        prefix = self._to_blob_path(resolved_path)
        if not prefix.endswith("/"):
            prefix += "/"

        cc = self._get_container_client()
        entries = set()

        try:
            from azure.core.exceptions import ResourceNotFoundError
        except ImportError:
            ResourceNotFoundError = Exception

        try:
            async for item in cc.list_blobs(name_starts_with=prefix):
                # Get relative name (strip prefix)
                rel = item.name[len(prefix):]
                # Direct children only (no nested paths)
                if "/" in rel:
                    # It's in a subdirectory — add the dir name
                    dir_name = rel.split("/")[0]
                    if dir_name:
                        entries.add(dir_name)
                elif rel:
                    entries.add(rel)
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Directory not found: {resolved_path}")
        except Exception as e:
            if "NotFound" in str(type(e).__name__) or "ContainerNotFound" in str(e):
                raise FileNotFoundError(f"Directory not found: {resolved_path}")
            raise

        return sorted(entries)

    async def _exists(self, resolved_path: str) -> bool:
        blob_path = self._to_blob_path(resolved_path)
        bc = self._get_blob_client(blob_path)

        try:
            exists = await bc.exists()
            if exists:
                return True
        except Exception:
            pass

        # Check if it's a "directory" (has blobs with this prefix)
        prefix = blob_path if blob_path.endswith("/") else blob_path + "/"
        cc = self._get_container_client()
        try:
            async for _ in cc.list_blobs(name_starts_with=prefix):
                return True
        except Exception:
            pass

        return False

    async def _is_dir(self, resolved_path: str) -> bool:
        prefix = self._to_blob_path(resolved_path)
        if not prefix.endswith("/"):
            prefix += "/"

        cc = self._get_container_client()
        try:
            async for _ in cc.list_blobs(name_starts_with=prefix):
                return True
        except Exception:
            pass
        return False

    async def delete(self, path: str) -> None:
        resolved = self._resolve(path)
        blob_path = self._to_blob_path(resolved)
        bc = self._get_blob_client(blob_path)

        try:
            await bc.delete_blob()
        except Exception:
            pass  # Blob doesn't exist

    async def close(self) -> None:
        """Close the Azure client."""
        if self._client:
            await self._client.close()
            self._client = None
