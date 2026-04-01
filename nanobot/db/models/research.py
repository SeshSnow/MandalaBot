"""Research document and execution tracking models."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from nanobot.db.base import Base
from nanobot.db.models.enums import ExecutionStatus, ResearchType


class ResearchDocument(Base):
    __tablename__ = "research_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id = Column(String(255), index=True, nullable=False)
    product_id = Column(String(255), nullable=True, index=True)
    document_type = Column(
        SQLEnum(ResearchType, name="research_type_enum", create_type=False), nullable=False,
    )
    content_markdown = Column(Text, nullable=False)
    azure_blob_url = Column(String(500), nullable=True)
    vector_store_file_id = Column(String(100), nullable=True)
    schema_version = Column(String(20), default="1.0.0", nullable=False)
    metadata_ = Column(JSON, default=dict, name="metadata")
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    parent_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self):
        return f"<ResearchDocument(type={self.document_type}, store={self.shopify_store_id})>"


class ResearchExecution(Base):
    __tablename__ = "research_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopify_store_id = Column(String(255), index=True, nullable=False)
    research_type = Column(
        SQLEnum(ResearchType, name="research_type_enum", create_type=False), nullable=False,
    )
    status = Column(
        SQLEnum(ExecutionStatus, name="execution_status_enum", create_type=False),
        default=ExecutionStatus.PENDING, nullable=False,
    )
    input_params = Column(JSON, default=dict)
    result_document_id = Column(
        UUID(as_uuid=True), ForeignKey("research_documents.id", ondelete="SET NULL"), nullable=True,
    )
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self):
        return f"<ResearchExecution(type={self.research_type}, status={self.status})>"
