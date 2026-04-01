"""ContextVar-based per-request tenant isolation.

Provides request-scoped storage for:
- Shop domain (tenant identifier)
- Store config (Shopify credentials loaded from DB)
- Request ID (for distributed tracing)

Each async task gets its own copy of these values, making concurrent
request handling safe without explicit parameter threading.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

_tenant_domain_var: ContextVar[str | None] = ContextVar("tenant_domain", default=None)
_store_config_var: ContextVar[dict[str, Any] | None] = ContextVar("store_config", default=None)
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


# ---------------------------------------------------------------------------
# Tenant domain
# ---------------------------------------------------------------------------

def set_tenant_context(shop_domain: str | None = None, request_id: str | None = None) -> None:
    """Set tenant identity for the current async context."""
    _tenant_domain_var.set(shop_domain)
    if request_id is not None:
        _request_id_var.set(request_id)


def clear_tenant_context() -> None:
    """Reset all tenant-scoped ContextVars (call in a finally block)."""
    _tenant_domain_var.set(None)
    _store_config_var.set(None)
    _request_id_var.set(None)


def get_tenant_domain() -> str | None:
    return _tenant_domain_var.get()


# ---------------------------------------------------------------------------
# Store config (Shopify credentials)
# ---------------------------------------------------------------------------

def set_store_config(config: dict[str, Any] | None) -> None:
    _store_config_var.set(config)


def get_store_config() -> dict[str, Any] | None:
    return _store_config_var.get()


# ---------------------------------------------------------------------------
# Request ID
# ---------------------------------------------------------------------------

def get_request_id() -> str | None:
    return _request_id_var.get()
