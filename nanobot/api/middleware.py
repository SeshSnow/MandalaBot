"""FastAPI middleware for tenant isolation and request tracing.

Extracts the Shopify shop domain from X-Shopify-Shop-Domain header,
sets per-request ContextVars for tenant identity and request ID,
and cleans up after the response is sent.

Routes without the header proceed without tenant context (e.g. /health,
vanilla nanobot OpenAI-compat endpoints).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from nanobot.tenant.context import clear_tenant_context, set_tenant_context

SHOP_DOMAIN_HEADER = "X-Shopify-Shop-Domain"


class TenantMiddleware(BaseHTTPMiddleware):
    """Sets tenant context and request ID for every incoming request.

    - If X-Shopify-Shop-Domain is present, the shop domain is stored in
      the tenant ContextVar so downstream code can access it without
      explicit parameter passing.
    - A unique request ID is always generated and attached to the response
      as X-Request-ID for distributed tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        shop_domain = request.headers.get(SHOP_DOMAIN_HEADER)
        request_id = uuid.uuid4().hex

        set_tenant_context(shop_domain=shop_domain, request_id=request_id)

        if shop_domain:
            logger.debug("TenantMiddleware: shop_domain={} request_id={}", shop_domain, request_id)

        try:
            response = await call_next(request)
        finally:
            clear_tenant_context()

        response.headers["X-Request-ID"] = request_id
        return response
