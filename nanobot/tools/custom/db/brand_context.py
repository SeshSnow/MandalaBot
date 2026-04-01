"""Tool for fetching brand context from the database.

This tool retrieves brand information for the current shop, including:
- Brand name and description
- Primary domain (for SEO/competitor research)
- Vector store ID (for RAG integration)
- Context configuration (product categories, attributes, etc.)
"""

from loguru import logger
from sqlalchemy import select

from nanobot.db.session import get_db_context
from nanobot.db.models.brand import Brand
from nanobot.services.shopify.shop_context import get_shop_store_config
from nanobot.tools.decorator import tool


@tool(
    description="Get the brand context for the current shop. "
    "Returns brand name, description, primary domain, vector store ID, "
    "and any configured context (product categories, attributes, etc.). "
    "This is useful for understanding the business before generating research."
)
async def get_brand_context() -> dict:
    """
    Get brand context for the current shop.

    Fetches the brand record from the database using the current shop context.
    Returns all available brand information including:
    - brand_name: The display name of the brand
    - description: Business description
    - primary_domain: Public domain (e.g., example.com) for SEO research
    - vector_id: OpenAI vector store ID for RAG
    - context_config: Additional brand configuration (categories, attributes)

    Returns:
        Dict with brand context or error information.
    """
    store_config = get_shop_store_config()
    if not store_config or not store_config.get("domain"):
        return {
            "success": False,
            "error": "Shop context not available. Ensure the request includes a valid shopify_store_id.",
        }

    shop_domain = store_config["domain"]
    try:
        async with get_db_context() as session:
            result = await session.execute(select(Brand).where(Brand.shopify_store_id == shop_domain))
            brand = result.scalars().first()

        if not brand:
            logger.warning(f"Brand not found for shop: {shop_domain}")
            return {
                "success": False,
                "error": f"Brand not found for shop: {shop_domain}. Ensure the brand has been created during shop initialization.",
            }

        context = {
            "success": True,
            "brand_name": brand.brand_name,
            "description": brand.description,
            "primary_domain": brand.primary_domain,
            "vector_id": brand.vector_id,
        }

        if brand.context_config_json:
            context["context_config"] = brand.context_config_json
        else:
            context["context_config"] = None

        return context

    except Exception as e:
        logger.exception(f"Error fetching brand context for shop {shop_domain}: {e}")
        return {
            "success": False,
            "error": f"Database error while fetching brand context: {str(e)}",
        }
