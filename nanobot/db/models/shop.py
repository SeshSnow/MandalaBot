"""Shop subscription and token tracking model."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from nanobot.db.base import Base


class ShopSubscription(Base):
    __tablename__ = "shop_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id = Column(String(255), nullable=False, unique=True, index=True)
    plan_name = Column(String(50), nullable=False, default="basic")
    subscription_id = Column(String(255), nullable=True)
    billing_interval = Column(String(20), nullable=True)
    tokens_remaining = Column(Integer, nullable=False, default=5)
    billing_cycle_start = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ShopSubscription(shopify_store_id={self.shopify_store_id}, plan={self.plan_name})>"
