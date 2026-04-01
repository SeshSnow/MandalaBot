"""Tools for saving and retrieving research documents.

These tools handle:
- Storing markdown content directly
- Deactivating existing documents of same type
- Uploading to Azure Blob Storage (optional)
- Creating database records
"""

from typing import Any, Literal
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from nanobot.db.session import async_session_factory
from nanobot.db.models.research import ResearchDocument
from nanobot.db.models.enums import ResearchType
from nanobot.services.shopify.shop_context import get_shop_store_config
from nanobot.tools.decorator import tool


async def _save_document(
    document_type: str,
    content_markdown: str,
    product_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Save a research document to the database (async).

    Args:
        document_type: Type of document (market_research, customer_avatar, competitor_analysis)
        content_markdown: Markdown content to store
        product_id: Optional product scope (null = store-level)
        metadata: Additional metadata

    Returns:
        Dict with document ID and status
    """
    store_config = get_shop_store_config()
    if not store_config or not store_config.get("domain"):
        return {
            "success": False,
            "error": "Shop context not available. Ensure the request includes a valid shopify_store_id.",
        }

    shop_domain = store_config["domain"]

    try:
        research_type = ResearchType(document_type)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid document type: {document_type}. Valid types: {[e.value for e in ResearchType]}",
        }

    if not content_markdown or not content_markdown.strip():
        return {
            "success": False,
            "error": "Content markdown cannot be empty.",
        }

    azure_blob_url = None
    try:
        from nanobot.config.mandala import MandalaConfig
        cfg = MandalaConfig()
        if cfg.azure_storage_connection_string:
            from nanobot.services.blob_storage import BlobStorageService
            blob_service = BlobStorageService(
                connection_string=cfg.azure_storage_connection_string,
                container_name=cfg.azure_storage_container,
            )
            if blob_service.is_available:
                logger.info("Blob storage available but skipping in tool context")
    except Exception as e:
        logger.warning(f"Failed to initialize blob storage: {e}")

    async with async_session_factory() as session:
        try:
            # Deactivate existing documents of the same type
            existing_result = await session.execute(
                select(ResearchDocument).where(
                    ResearchDocument.shopify_store_id == shop_domain,
                    ResearchDocument.document_type == research_type,
                    ResearchDocument.active == True,  # noqa: E712
                )
            )
            existing_docs = existing_result.scalars().all()

            deactivated_count = 0
            for doc in existing_docs:
                doc.active = False
                deactivated_count += 1

            if deactivated_count > 0:
                logger.info(f"Deactivated {deactivated_count} existing {document_type} document(s) for {shop_domain}")

            doc = ResearchDocument(
                shopify_store_id=shop_domain,
                product_id=product_id,
                document_type=research_type,
                content_markdown=content_markdown,
                azure_blob_url=azure_blob_url,
                metadata_=metadata or {},
                active=True,
            )

            session.add(doc)
            await session.commit()
            await session.refresh(doc)

            logger.info(f"Saved {document_type} document {doc.id} for {shop_domain}")

            return {
                "success": True,
                "document_id": str(doc.id),
                "document_type": document_type,
                "shop_domain": shop_domain,
                "deactivated_count": deactivated_count,
                "azure_blob_url": azure_blob_url,
            }

        except Exception as e:
            await session.rollback()
            logger.exception(f"Error saving research document: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
            }


async def _get_document(
    document_type: str,
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve a research document from the database (async).

    Args:
        document_type: Type of document to retrieve
        document_id: Optional specific document ID (otherwise gets latest active)

    Returns:
        Dict with document content or error
    """
    store_config = get_shop_store_config()
    if not store_config or not store_config.get("domain"):
        return {
            "success": False,
            "error": "Shop context not available.",
        }

    shop_domain = store_config["domain"]

    try:
        research_type = ResearchType(document_type)
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid document type: {document_type}. Valid types: {[e.value for e in ResearchType]}",
        }

    async with async_session_factory() as session:
        try:
            if document_id:
                try:
                    doc_uuid = UUID(document_id)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"Invalid document ID format: {document_id}",
                    }

                result = await session.execute(
                    select(ResearchDocument).where(
                        ResearchDocument.id == doc_uuid,
                        ResearchDocument.shopify_store_id == shop_domain,
                    )
                )
                doc = result.scalar_one_or_none()
            else:
                result = await session.execute(
                    select(ResearchDocument)
                    .where(
                        ResearchDocument.shopify_store_id == shop_domain,
                        ResearchDocument.document_type == research_type,
                        ResearchDocument.active == True,  # noqa: E712
                    )
                    .order_by(ResearchDocument.created_at.desc())
                    .limit(1)
                )
                doc = result.scalar_one_or_none()

            if not doc:
                return {
                    "success": False,
                    "error": f"No {document_type} document found for shop: {shop_domain}",
                    "document_type": document_type,
                }

            return {
                "success": True,
                "document_id": str(doc.id),
                "document_type": document_type,
                "content": doc.content_markdown,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "active": doc.active,
                "azure_blob_url": doc.azure_blob_url,
            }

        except Exception as e:
            logger.exception(f"Error retrieving research document: {e}")
            return {
                "success": False,
                "error": f"Database error: {str(e)}",
            }


@tool(
    description="Save a research document to the database. "
    "Stores the markdown content directly, "
    "deactivates any existing active documents of the same type, "
    "and creates a new database record. "
    "Supported document types: market_research, customer_avatar, competitor_analysis."
)
async def save_research_document(
    document_type: Literal["market_research", "customer_avatar", "competitor_analysis"],
    content_markdown: str,
    product_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Save a research document to the database.

    Args:
        document_type: Type of document to save
        content_markdown: Markdown content to store
        product_id: Optional product scope (null = store-level)
        metadata: Additional metadata (data sources, generation params, etc.)

    Returns:
        Dict with document ID, status, and any errors
    """
    return await _save_document(
        document_type=document_type,
        content_markdown=content_markdown,
        product_id=product_id,
        metadata=metadata,
    )


@tool(
    description="Get a research document from the database. Returns the latest active document of the specified type, or a specific document by ID."
)
async def get_research_document(
    document_type: Literal["market_research", "customer_avatar", "competitor_analysis"],
    document_id: str | None = None,
) -> dict[str, Any]:
    """
    Get a research document from the database.

    Args:
        document_type: Type of document to retrieve
        document_id: Optional specific document ID (otherwise gets latest active)

    Returns:
        Dict with document content or error
    """
    return await _get_document(
        document_type=document_type,
        document_id=document_id,
    )
