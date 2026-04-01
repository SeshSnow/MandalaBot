"""
SE Ranking domain research tools for nanobot.

Provides tools to query SE Ranking API for domain overview, top pages,
and domain keywords.
"""

from nanobot.services.seo.seranking import SERankingClient
from nanobot.services.shopify.shop_context import get_primary_domain_for_current_shop_async
from nanobot.tools.decorator import tool


@tool(
    description=(
        "Get domain overview/authority metrics for a domain using SE Ranking. "
        "Returns authority and visibility metrics. Use with_subdomains=1 to include subdomains, "
        "or url to analyze a specific page. If domain is omitted, uses the store's primary domain "
        "(actual storefront URL)."
    )
)
async def seranking_domain_overview(
    domain: str | None = None,
    source: str = "us",
    with_subdomains: int = 1,
    url: str | None = None,
) -> dict:
    """
    Get domain overview and authority metrics for a domain.

    Returns SE Ranking domain authority and visibility data. Optionally
    analyze a specific URL or include/exclude subdomains. If domain is omitted,
    uses the store's primary domain from brand config.
    """
    source = source or "us"
    if not domain:
        domain = await get_primary_domain_for_current_shop_async()
    if not domain:
        return {
            "error": ("No domain provided and store primary domain is not configured. Either pass a domain or ensure brand.primary_domain is set."),
            "domain": None,
        }
    try:
        client = SERankingClient()
        response = await client.get_domain_overview(
            domain=domain,
            source=source,
            with_subdomains=with_subdomains,
            url=url,
        )
        return {"domain": domain, "source": source, "data": response}
    except Exception as e:
        return {"error": str(e), "domain": domain}


@tool(
    description=(
        "Get top-performing pages for a domain using SE Ranking. "
        "Pass target (domain or URL), scope ('domain' or 'url'), and optional order_field "
        "(e.g. traffic_sum), type ('organic'), limit. If target is omitted, uses the store's "
        "primary domain."
    )
)
async def seranking_domain_pages(
    target: str | None = None,
    scope: str = "domain",
    source: str = "us",
    type: str = "organic",
    order_field: str = "traffic_sum",
    limit: int = 10,
) -> dict:
    """
    Get top-performing pages for a domain or URL.

    Returns pages ranked by traffic or other metrics. Scope is 'domain' for
    the whole site or 'url' for a single page. Order by traffic_sum or other
    supported fields. If target is omitted, uses the store's primary domain.
    """
    source = source or "us"
    scope = scope or "domain"
    limit = max(1, min(100, limit if limit is not None else 10))
    if not target:
        target = await get_primary_domain_for_current_shop_async()
    if not target:
        return {
            "error": ("No target provided and store primary domain is not configured. Either pass target or ensure brand.primary_domain is set."),
            "target": None,
        }
    try:
        client = SERankingClient()
        response = await client.get_domain_pages(
            target=target,
            scope=scope,
            source=source,
            type=type,
            order_field=order_field,
            limit=limit,
        )
        return {"target": target, "scope": scope, "source": source, "data": response}
    except Exception as e:
        return {"error": str(e), "target": target}


@tool(
    description=(
        "Get top keywords that drive traffic to a domain using SE Ranking. "
        "Returns keywords with traffic and ranking metrics. Optional: type ('organic'), "
        "order_field ('traffic'), limit. If domain is omitted, uses the store's primary domain."
    )
)
async def seranking_domain_keywords(
    domain: str | None = None,
    source: str = "us",
    type: str = "organic",
    order_field: str = "traffic",
    limit: int = 20,
) -> dict:
    """
    Get top keywords for a domain.

    Returns keywords that drive organic (or other) traffic to the domain,
    ordered by traffic or other metrics. If domain is omitted, uses the
    store's primary domain from brand config.
    """
    source = source or "us"
    limit = max(1, min(100, limit if limit is not None else 20))
    if not domain:
        domain = await get_primary_domain_for_current_shop_async()
    if not domain:
        return {
            "error": ("No domain provided and store primary domain is not configured. Either pass a domain or ensure brand.primary_domain is set."),
            "domain": None,
        }
    try:
        client = SERankingClient()
        response = await client.get_domain_keywords(
            domain=domain,
            source=source,
            type=type,
            order_field=order_field,
            limit=limit,
        )
        return {"domain": domain, "source": source, "data": response}
    except Exception as e:
        return {"error": str(e), "domain": domain}
