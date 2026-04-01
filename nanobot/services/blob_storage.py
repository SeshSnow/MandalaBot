"""
Async Azure Blob Storage service for nanobot attachments.

Provides upload, SAS URL generation, and delete operations.
Azure imports are lazy so the app can start without azure-storage-blob installed.
"""

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


class AzureBlobError(Exception):
    """Raised when Azure Blob Storage operations fail."""

    pass


class BlobStorageService:
    """
    Async Azure Blob Storage service for conversation attachments.

    Uses azure.storage.blob.aio for async operations.
    """

    def __init__(
        self,
        connection_string: str | None,
        container_name: str = "nanobot-attachments",
    ) -> None:
        """
        Initialize the blob storage service.

        Args:
            connection_string: Azure Storage connection string.
            container_name: Container for attachment blobs.
        """
        self._connection_string = connection_string
        self._container_name = container_name
        self._client = None
        self._account_name = None
        self._account_key = None

        if connection_string:
            self._parse_connection_string(connection_string)
            self._init_client()

    def _parse_connection_string(self, conn_str: str) -> None:
        """Extract account name and key from connection string."""
        parts = {}
        for part in conn_str.split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                parts[key.strip().lower()] = value.strip()
        self._account_name = parts.get("accountname")
        self._account_key = parts.get("accountkey")

    def _init_client(self) -> None:
        """Initialize the async blob service client."""
        if not self._connection_string:
            return
        try:
            from azure.storage.blob.aio import BlobServiceClient

            self._client = BlobServiceClient.from_connection_string(self._connection_string)
            logger.info("Azure Blob Storage client initialized")
        except ImportError as e:
            logger.warning("azure-storage-blob not installed; blob storage disabled: %s", e)
            self._client = None
        except Exception as e:
            logger.warning("Failed to initialize Azure Blob Storage client: %s", e)
            self._client = None

    @property
    def is_available(self) -> bool:
        """Return True if blob storage is configured and available."""
        return self._client is not None

    async def _ensure_container_exists(self) -> None:
        """Create container if it does not exist."""
        if not self._client:
            raise AzureBlobError("Azure Blob Storage client not initialized")
        container_client = self._client.get_container_client(self._container_name)
        if not await container_client.exists():
            await container_client.create_container()
            logger.info("Created container: %s", self._container_name)

    async def upload_blob(
        self,
        content: bytes,
        path: str,
        content_type: str,
    ) -> str:
        """
        Upload blob content to Azure Storage.

        Args:
            content: Raw bytes to upload.
            path: Blob path (e.g., "shop_id/conv_id/uuid.png").
            content_type: MIME type (e.g., "image/png").

        Returns:
            Public blob URL (base URL; for private containers use get_sas_url).

        Raises:
            AzureBlobError: If upload fails.
        """
        if not self._client:
            raise AzureBlobError("Azure Blob Storage client not initialized")

        await self._ensure_container_exists()

        blob_client = self._client.get_blob_client(
            container=self._container_name,
            blob=path,
        )
        from azure.core.exceptions import AzureError
        from azure.storage.blob import ContentSettings

        content_settings = ContentSettings(content_type=content_type)
        try:
            await blob_client.upload_blob(
                data=content,
                overwrite=True,
                content_settings=content_settings,
            )
            return blob_client.url
        except AzureError as e:
            logger.error("Azure Blob upload failed: %s", e)
            raise AzureBlobError(f"Failed to upload blob: {e}") from e

    def get_sas_url(self, path: str, expiry_hours: int = 1) -> str:
        """
        Generate a temporary SAS URL for blob access.

        Args:
            path: Blob path within the container.
            expiry_hours: URL validity in hours.

        Returns:
            Full URL with SAS token for read access.

        Raises:
            AzureBlobError: If SAS generation fails.
        """
        if not self._account_name or not self._account_key:
            raise AzureBlobError("Cannot generate SAS: account credentials not available")

        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        expiry = datetime.now(UTC) + timedelta(hours=expiry_hours)
        sas_token = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            blob_name=path,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        base_url = f"https://{self._account_name}.blob.core.windows.net/{self._container_name}/{path}"
        return f"{base_url}?{sas_token}"

    async def delete_blob(self, path: str) -> bool:
        """
        Delete a blob from storage.

        Args:
            path: Blob path within the container.

        Returns:
            True if deleted, False if blob did not exist or client unavailable.
        """
        if not self._client:
            return False

        blob_client = self._client.get_blob_client(
            container=self._container_name,
            blob=path,
        )
        from azure.core.exceptions import AzureError

        try:
            await blob_client.delete_blob()
            return True
        except AzureError as e:
            logger.warning("Failed to delete blob %s: %s", path, e)
            return False

    async def close(self) -> None:
        """Close the blob service client."""
        if self._client:
            await self._client.close()
            self._client = None
