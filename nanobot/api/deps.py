"""FastAPI dependency injection for nanobot API routes.

Centralizes extraction of shop domain from the X-Shopify-Shop-Domain
header (set by mandala-shopify-app proxy from session.shop).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException


async def get_shop_domain(
    x_shopify_shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
) -> str | None:
    """Return the shop domain from the request header, or None if absent.

    Lenient version: allows requests without a shop domain for backward
    compatibility with vanilla nanobot OpenAI-compat clients.
    """
    if x_shopify_shop_domain:
        return str(x_shopify_shop_domain).strip() or None
    return None


async def require_shop_domain(
    x_shopify_shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
) -> str:
    """Return the shop domain, raising 400 if missing.

    Use on routes that require tenant context.
    """
    if not x_shopify_shop_domain or not str(x_shopify_shop_domain).strip():
        raise HTTPException(
            status_code=400,
            detail="X-Shopify-Shop-Domain header is required",
        )
    return str(x_shopify_shop_domain).strip()
