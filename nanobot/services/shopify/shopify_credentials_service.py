"""
Service for encrypting, validating, and storing Shopify Admin API credentials.
"""

from __future__ import annotations

import asyncio
import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.shopify_credentials import ShopifyStoreCredential
from nanobot.services.shopify.graphql.queries import GET_SHOP_DOMAIN
from nanobot.services.shopify.shopify_client import ShopifyClient


class ShopifyCredentialsService:
    """
    Service to validate Shopify tokens and persist encrypted credentials per shop.
    """

    def __init__(self, encryption_key: str | None = None) -> None:
        """
        Initialize the credentials service.

        Args:
            encryption_key: Optional Fernet key; defaults to env var
                SHOPIFY_TOKEN_ENCRYPTION_KEY.
        """
        self._encryption_key = encryption_key or os.getenv("SHOPIFY_TOKEN_ENCRYPTION_KEY")
        if not self._encryption_key:
            raise ValueError("SHOPIFY_TOKEN_ENCRYPTION_KEY is not configured in the environment")
        self._fernet = Fernet(self._encryption_key)

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a Shopify access token.

        Args:
            token: Shopify Admin API access token

        Returns:
            Encrypted token string
        """
        return self._fernet.encrypt(token.encode("utf-8")).decode("utf-8")

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a Shopify access token.

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Decrypted token string
        """
        try:
            return self._fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encryption key or corrupted token") from exc

    def validate_token_for_shop(self, shopify_store_id: str, token: str) -> None:
        """
        Validate that the provided token belongs to the expected shop domain.

        Sync; calls Shopify client. Use asyncio.to_thread when calling from async.

        Args:
            shopify_store_id: Expected Shopify shop domain
            token: Shopify Admin API access token

        Raises:
            ValueError: If the token does not belong to the expected shop
        """
        shopify_client = ShopifyClient(
            {
                "domain": shopify_store_id,
                "accessToken": token,
                "apiVersion": "2025-04",
            }
        )
        result = shopify_client.execute_query(GET_SHOP_DOMAIN)
        shop = result.get("shop") or {}
        domain = shop.get("myshopifyDomain")
        if not domain or domain != shopify_store_id:
            raise ValueError(f"Shopify token does not match expected shop domain: {shopify_store_id}")

    async def upsert_credentials(
        self,
        shopify_store_id: str,
        token: str,
        db: AsyncSession,
        api_version: str | None = None,
    ) -> ShopifyStoreCredential:
        """
        Validate and upsert encrypted credentials for a shop.

        Args:
            shopify_store_id: Shopify shop domain
            token: Shopify Admin API access token
            db: Async database session
            api_version: Optional Shopify API version to store

        Returns:
            ShopifyStoreCredential record
        """
        await asyncio.to_thread(self.validate_token_for_shop, shopify_store_id, token)
        encrypted_token = self.encrypt_token(token)

        result = await db.execute(select(ShopifyStoreCredential).where(ShopifyStoreCredential.shopify_store_id == shopify_store_id))
        credential = result.scalars().first()

        if not credential:
            credential = ShopifyStoreCredential(
                shopify_store_id=shopify_store_id,
                access_token_encrypted=encrypted_token,
                api_version=api_version or "2025-04",
            )
            db.add(credential)
        else:
            credential.access_token_encrypted = encrypted_token
            if api_version:
                credential.api_version = api_version

        await db.commit()
        await db.refresh(credential)
        return credential

    async def get_credentials(self, shopify_store_id: str, db: AsyncSession) -> ShopifyStoreCredential:
        """
        Get stored credentials for a shop.

        Args:
            shopify_store_id: Shopify shop domain
            db: Async database session

        Returns:
            ShopifyStoreCredential record

        Raises:
            ValueError: If credentials are not found
        """
        result = await db.execute(select(ShopifyStoreCredential).where(ShopifyStoreCredential.shopify_store_id == shopify_store_id))
        credential = result.scalars().first()
        if not credential:
            raise ValueError(f"No Shopify credentials found for domain: {shopify_store_id}")
        return credential

    async def get_token(self, shopify_store_id: str, db: AsyncSession) -> str:
        """
        Get decrypted Shopify token for a shop.

        Args:
            shopify_store_id: Shopify shop domain
            db: Async database session

        Returns:
            Decrypted Shopify token
        """
        credential = await self.get_credentials(shopify_store_id, db)
        return self.decrypt_token(credential.access_token_encrypted)
