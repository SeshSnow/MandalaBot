"""Shopify Admin API credentials (encrypted at rest)."""

import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from nanobot.db.base import Base


class ShopifyStoreCredential(Base):
    __tablename__ = "shopify_store_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id = Column(String(255), nullable=False, unique=True, index=True)
    access_token_encrypted = Column(String(4096), nullable=False)
    api_version = Column(String(32), nullable=True, default="2025-04")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ShopifyStoreCredential(shopify_store_id={self.shopify_store_id})>"
