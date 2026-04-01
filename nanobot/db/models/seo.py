"""SEO article, keyword suggestion, and pipeline execution models."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from nanobot.db.base import Base


class SEOArticle(Base):
    __tablename__ = "seo_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    abstract = Column(String(2000))
    status = Column(String(50), nullable=False, default="outline_generated")
    shopify_article_id = Column(String(255), nullable=True)
    shopify_article_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    brand = relationship("Brand", backref="seo_articles")


class KeywordSuggestion(Base):
    __tablename__ = "keyword_suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False, index=True)
    keyword = Column(String(500), nullable=False, index=True)
    volume = Column(Integer, nullable=False, default=0)
    difficulty = Column(Integer, nullable=False, default=0)
    source = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    brand = relationship("Brand", backref="keyword_suggestions")


class PipelineExecution(Base):
    __tablename__ = "pipeline_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_type = Column(String(50), nullable=False)
    execution_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    input_data = Column(JSON, nullable=False)
    result_data = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime)
    created_by = Column(String(255))
    shop_domain = Column(String(255), nullable=True, index=True)
    metadata_ = Column(JSON, name="metadata")
