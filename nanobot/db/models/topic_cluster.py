"""Topic cluster hierarchy: TopicCluster -> TopicKeyword -> TopicPage -> LongTailKeyword + ScheduledArticle."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from nanobot.db.base import Base


class TopicCluster(Base):
    __tablename__ = "topic_clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False, index=True)
    seed_keyword = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    topic_keywords = relationship("TopicKeyword", back_populates="topic_cluster", cascade="all, delete-orphan")
    scheduled_articles = relationship("ScheduledArticle", back_populates="topic_cluster", cascade="all, delete-orphan")


class TopicKeyword(Base):
    __tablename__ = "topic_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_cluster_id = Column(UUID(as_uuid=True), ForeignKey("topic_clusters.id"), nullable=False, index=True)
    keyword = Column(String(500), nullable=False)
    volume = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=False)
    relevance = Column(Float, nullable=False, default=1.0)
    cpc = Column(Float, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    seo_article_id = Column(UUID(as_uuid=True), ForeignKey("seo_articles.id"), nullable=True, index=True)
    article_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    topic_cluster = relationship("TopicCluster", back_populates="topic_keywords")
    pages = relationship("TopicPage", back_populates="topic_keyword", cascade="all, delete-orphan")


class TopicPage(Base):
    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_keyword_id = Column(UUID(as_uuid=True), ForeignKey("topic_keywords.id"), nullable=False, index=True)
    target_keyword = Column(String(500), nullable=False)
    is_pillar = Column(Boolean, nullable=False, default=False)
    keyword_difficulty = Column(Integer, nullable=False)
    search_volume = Column(Integer, nullable=False)
    relevance = Column(Float, nullable=False, default=1.0)
    cpc = Column(Float, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    seo_article_id = Column(UUID(as_uuid=True), ForeignKey("seo_articles.id"), nullable=True, index=True)
    article_created_at = Column(DateTime, nullable=True)
    content_guidance = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    topic_keyword = relationship("TopicKeyword", back_populates="pages")
    longtail_keywords = relationship("LongTailKeyword", back_populates="page", cascade="all, delete-orphan")


class LongTailKeyword(Base):
    __tablename__ = "longtail_keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"), nullable=False, index=True)
    keyword = Column(String(500), nullable=False)
    volume = Column(Integer, nullable=False)
    difficulty = Column(Integer, nullable=False)
    relevance = Column(Float, nullable=False, default=1.0)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())

    page = relationship("TopicPage", back_populates="longtail_keywords")


class ScheduledArticle(Base):
    __tablename__ = "scheduled_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=False, index=True)
    topic_cluster_id = Column(UUID(as_uuid=True), ForeignKey("topic_clusters.id"), nullable=False, index=True)
    keyword = Column(String(500), nullable=False)
    article_type = Column(String(20), nullable=False)
    scheduled_datetime = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(10), nullable=False, default="0")
    topic_keyword_id = Column(UUID(as_uuid=True), ForeignKey("topic_keywords.id"), nullable=True, index=True)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    topic_cluster = relationship("TopicCluster", back_populates="scheduled_articles")
    topic_keyword = relationship("TopicKeyword", foreign_keys=[topic_keyword_id])
    page = relationship("TopicPage", foreign_keys=[page_id])
