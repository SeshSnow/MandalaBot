"""
Per-request Shopify store configuration context.

Store config (domain, accessToken, apiVersion) is provided by the front-end
via headers/body or loaded from the DB by shop domain. The agent loop sets
this context when processing a chat request so tools (e.g. top_selling_products)
can use the current shop's credentials without reading env vars.
"""

from contextvars import ContextVar
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.brand import Brand

_store_config_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "shop_store_config",
    default=None,
)


def set_shop_store_config(store_config: dict[str, Any] | None) -> None:
    """
    Set the current request's Shopify store config (domain, accessToken, apiVersion).

    Called by the agent loop when shopify_store_id is present; config is loaded from DB.
    """
    _store_config_var.set(store_config)


# Alias used by nanobot.tenant.context
set_store_config = set_shop_store_config


def get_shop_store_config() -> dict[str, Any] | None:
    """
    Get the current request's Shopify store config if set.

    Returns:
        Store config dict with domain, accessToken, apiVersion, or None if not set.
    """
    return _store_config_var.get()


async def get_store_config_for_shop_from_db_async(session: AsyncSession, shopify_store_id: str) -> dict[str, Any] | None:
    """
    Load Shopify store config from the database by shop domain (async).

    Used by the agent loop to set shop context when processing chat with shopify_store_id.

    Args:
        session: Async database session
        shopify_store_id: Shopify shop domain (e.g. "store.myshopify.com")

    Returns:
        Store config dict with domain, accessToken, apiVersion, or None if not found.
    """
    from nanobot.config.mandala import MandalaConfig
    from nanobot.services.shopify.shopify_credentials_service import ShopifyCredentialsService

    if not shopify_store_id:
        return None
    try:
        cfg = MandalaConfig()
        credentials_service = ShopifyCredentialsService(
            encryption_key=cfg.shopify_token_encryption_key or None,
        )
        creds = await credentials_service.get_credentials(shopify_store_id, session)
        token = credentials_service.decrypt_token(creds.access_token_encrypted)
        return {
            "domain": shopify_store_id,
            "accessToken": token,
            "apiVersion": getattr(creds, "api_version", None) or "2025-04",
        }
    except ValueError as e:
        logger.warning(
            "Shopify credentials not found or invalid for shop {}: {}",
            shopify_store_id,
            e,
        )
        return None
    except Exception as e:
        logger.exception(
            "Failed to load Shopify credentials for shop {}: {}",
            shopify_store_id,
            e,
        )
        return None


async def get_primary_domain_for_current_shop_async() -> str | None:
    """
    Fetch the brand's primary_domain for the current shop context from DB.

    Uses the shop domain from get_shop_store_config() to look up the Brand
    and return its primary_domain (e.g., example.com), distinct from *.myshopify.com.
    Creates its own session via get_db_context.

    Returns:
        The primary domain string, or None if not set or shop context unavailable.
    """
    store_config = get_shop_store_config()
    if not store_config or not store_config.get("domain"):
        return None
    shop_domain = store_config["domain"]

    from nanobot.db.session import get_db_context

    async with get_db_context() as session:
        result = await session.execute(select(Brand).where(Brand.shopify_store_id == shop_domain))
        brand = result.scalars().first()
        return brand.primary_domain if brand else None
