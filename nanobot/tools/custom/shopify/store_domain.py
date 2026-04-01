"""Tool for fetching the store's primary domain from Shopify brand config."""

from nanobot.services.shopify.shop_context import get_primary_domain_for_current_shop_async
from nanobot.tools.decorator import tool


@tool(
    description="Get the store's primary domain (actual storefront URL, e.g. example.com). "
    "Returns the public domain configured for SEO/competitor research, not the *.myshopify.com URL."
)
async def get_store_primary_domain() -> dict:
    """
    Get the primary domain for the current store.

    Returns the brand's primary_domain (the actual storefront URL such as example.com),
    which is used for SEO research tools like SE Ranking. Returns an error if the domain
    is not configured or shop context is unavailable.
    """
    primary_domain = await get_primary_domain_for_current_shop_async()
    if not primary_domain:
        return {
            "success": False,
            "error": (
                "Primary domain is not configured for this shop. Ensure the brand has primary_domain set (typically during shop initialization)."
            ),
            "primary_domain": None,
        }
    return {
        "success": True,
        "primary_domain": primary_domain,
    }
