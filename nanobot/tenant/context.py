"""
Per-request tenant context via ContextVar.

TenantContext holds the shop domain and store config for the current request.
Set by TenantMiddleware; consumed by tools and services that need tenant identity.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantContext:
    """Request-scoped tenant identity and store configuration."""

    shop_domain: str
    store_config: dict[str, Any] = field(default_factory=dict)


_tenant_context_var: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


def set_tenant_context(shop_domain: str, store_config: dict[str, Any] | None = None) -> None:
    """Set the tenant context for the current request."""
    _tenant_context_var.set(TenantContext(shop_domain=shop_domain, store_config=store_config or {}))


def get_tenant_context() -> TenantContext | None:
    """Return the current request's tenant context, or None if not set."""
    return _tenant_context_var.get()


def clear_tenant_context() -> None:
    """Clear the tenant context (e.g. after request completes)."""
    _tenant_context_var.set(None)


def get_shop_domain() -> str | None:
    """Convenience helper: return the shop domain or None."""
    ctx = _tenant_context_var.get()
    return ctx.shop_domain if ctx else None


def set_store_config(store_config: dict[str, Any]) -> None:
    """Update the store config on the existing tenant context."""
    ctx = _tenant_context_var.get()
    if ctx is not None:
        ctx.store_config = store_config
