"""
FastAPI middleware for Mandala tenant isolation.

Extracts the Shopify shop domain from X-Shopify-Shop-Domain request header,
loads store credentials from the database, and sets the per-request
TenantContext and shop store config ContextVars before the request handler runs.

Routes that don't include this header proceed without tenant context (e.g.
the base nanobot OpenAI-compat endpoints).
"""

from collections.abc import Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from nanobot.tenant.context import clear_tenant_context, set_tenant_context

SHOP_DOMAIN_HEADER = "X-Shopify-Shop-Domain"


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Sets TenantContext and shop store config for each request that carries
    an X-Shopify-Shop-Domain header.

    Requires DB to be initialized (nanobot.db.session must be ready).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        shop_domain = request.headers.get(SHOP_DOMAIN_HEADER)

        if not shop_domain:
            return await call_next(request)

        set_tenant_context(shop_domain=shop_domain)

        try:
            store_config = await self._load_store_config(shop_domain)
            if store_config:
                from nanobot.services.shopify.shop_context import set_shop_store_config
                set_shop_store_config(store_config)
                from nanobot.tenant.context import set_store_config
                set_store_config(store_config)
        except Exception as e:
            logger.warning("TenantMiddleware: failed to load store config for {}: {}", shop_domain, e)

        try:
            response = await call_next(request)
        finally:
            clear_tenant_context()
            try:
                from nanobot.services.shopify.shop_context import set_shop_store_config
                set_shop_store_config(None)
            except Exception:
                pass

        return response

    async def _load_store_config(self, shop_domain: str) -> dict | None:
        try:
            from nanobot.db.session import get_db_context
            from nanobot.services.shopify.shop_context import get_store_config_for_shop_from_db_async

            async with get_db_context() as session:
                return await get_store_config_for_shop_from_db_async(session, shop_domain)
        except Exception as e:
            logger.debug("TenantMiddleware: could not load credentials for {}: {}", shop_domain, e)
            return None
