"""S3 remote storage backend.

Provides S3-backed workspace storage for multi-tenant, multi-machine deployments.
Requires: pip install boto3 (or aioboto3 for async).
"""

from __future__ import annotations

from nanobot.storage.base import StorageBackend


class S3Backend(StorageBackend):
    """Amazon S3 storage backend."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        allowed_prefix: str = "",
    ):
        super().__init__(root=prefix, allowed_prefix=allowed_prefix)
        self.bucket = bucket
        self.region = region
        self._client = None

    def _get_client(self):
        """Lazy-initialize S3 client."""
        if self._client is None:
            import boto3
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _to_key(self, resolved_path: str) -> str:
        """Convert resolved path to S3 key."""
        return resolved_path.lstrip("/")

    async def _read(self, resolved_path: str) -> str:
        import asyncio
        client = self._get_client()
        key = self._to_key(resolved_path)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.get_object(Bucket=self.bucket, Key=key)
        )
        return response["Body"].read().decode("utf-8")

    async def _write(self, resolved_path: str, content: str) -> None:
        import asyncio
        client = self._get_client()
        key = self._to_key(resolved_path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
            )
        )

    async def _list(self, resolved_path: str) -> list[str]:
        import asyncio
        client = self._get_client()
        prefix = self._to_key(resolved_path)
        if not prefix.endswith("/"):
            prefix += "/"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter="/",
            )
        )

        entries = set()

        # Files directly under this prefix
        for obj in response.get("Contents", []):
            name = obj["Key"][len(prefix):]
            if "/" not in name and name:
                entries.add(name)

        # Subdirectories (common prefixes)
        for cp in response.get("CommonPrefixes", []):
            name = cp["Prefix"][len(prefix):].rstrip("/")
            if name:
                entries.add(name)

        return sorted(entries)

    async def _exists(self, resolved_path: str) -> bool:
        import asyncio
        client = self._get_client()
        key = self._to_key(resolved_path)

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: client.head_object(Bucket=self.bucket, Key=key)
            )
            return True
        except Exception:
            # Check if it's a "directory" (has objects with this prefix)
            prefix = key if key.endswith("/") else key + "/"
            response = await loop.run_in_executor(
                None,
                lambda: client.list_objects_v2(
                    Bucket=self.bucket, Prefix=prefix, MaxKeys=1
                )
            )
            return bool(response.get("Contents"))

    async def _is_dir(self, resolved_path: str) -> bool:
        import asyncio
        client = self._get_client()
        prefix = self._to_key(resolved_path)
        if not prefix.endswith("/"):
            prefix += "/"

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.list_objects_v2(
                Bucket=self.bucket, Prefix=prefix, MaxKeys=1
            )
        )
        return bool(response.get("Contents"))

    async def delete(self, path: str) -> None:
        import asyncio
        client = self._get_client()
        resolved = self._resolve(path)
        key = self._to_key(resolved)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: client.delete_object(Bucket=self.bucket, Key=key)
        )
