"""Brand context model."""

import uuid

from sqlalchemy import JSON, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from nanobot.db.base import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id = Column(String(255), nullable=False, unique=True, index=True)
    brand_name = Column(String(500), nullable=False)
    description = Column(String(2000))
    primary_domain = Column(String(500), nullable=True)
    vector_id = Column(String(255), nullable=True, index=True)
    context_config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Brand(shopify_store_id={self.shopify_store_id}, brand_name={self.brand_name})>"
