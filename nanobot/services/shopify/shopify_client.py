"""
Client for interacting with the Shopify Admin API.
Handles authentication, request formatting, and response parsing.

Supports both sync and async operations via httpx (no gql dependency).
Credentials come from the request (front-end or DB), not from env vars.
"""

from typing import Any

import httpx
from loguru import logger

from nanobot.services.shopify.shop_context import get_shop_store_config

# Lazy import to avoid circular dependency
_blog_api_class = None


def _get_blog_api_class():
    """Lazy import BlogApi to avoid circular dependency."""
    global _blog_api_class
    if _blog_api_class is None:
        from nanobot.services.shopify.blog_api import BlogApi

        _blog_api_class = BlogApi
    return _blog_api_class


class ShopifyClient:
    """
    Client for interacting with the Shopify Admin API.
    Provides both sync and async GraphQL execution via HTTP.
    """

    def __init__(
        self,
        store_config: dict[str, Any] | None = None,
        domain: str | None = None,
        access_token: str | None = None,
        api_version: str | None = None,
    ):
        """
        Initialize the Shopify client.

        Can be initialized with store_config dict, individual parameters, or
        (when none provided) the current request's store config from context
        (set by the agent/API from front-end header or DB).

        Args:
            store_config: Configuration dict with domain, accessToken, apiVersion
            domain: Shop domain (e.g., "example.myshopify.com")
            access_token: Shopify Admin API access token
            api_version: API version (default: "2025-04")
        """
        if store_config:
            self.domain = store_config.get("domain")
            self.access_token = store_config.get("accessToken")
            self.api_version = store_config.get("apiVersion", "2025-04")
        elif domain and access_token:
            self.domain = domain
            self.access_token = access_token
            self.api_version = api_version or "2025-04"
        else:
            ctx = get_shop_store_config()
            if ctx:
                self.domain = ctx.get("domain")
                self.access_token = ctx.get("accessToken")
                self.api_version = ctx.get("apiVersion", "2025-04")
            else:
                self.domain = None
                self.access_token = None
                self.api_version = api_version or "2025-04"

        if not self.domain or not self.access_token:
            raise ValueError(
                "Missing required Shopify configuration. "
                "Provide store_config or (domain + access_token), or ensure the request "
                "includes X-Shopify-Shop-Domain and credentials are set (e.g. from DB)."
            )

        self.graphql_url = f"https://{self.domain}/admin/api/{self.api_version}/graphql.json"
        self._headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        self._async_client: httpx.AsyncClient | None = None
        self._blog: Any | None = None

    @property
    def blog(self) -> Any:
        """
        Get the BlogApi instance for managing blog articles.

        Returns:
            BlogApi instance.
        """
        if self._blog is None:
            BlogApi = _get_blog_api_class()
            self._blog = BlogApi(self)
        return self._blog

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                headers=self._headers,
                timeout=30.0,
            )
        return self._async_client

    def execute_query(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query or mutation synchronously.

        Args:
            query: The GraphQL query/mutation as string
            variables: Optional variables for the query

        Returns:
            The query result (data or errors from response)

        Raises:
            ValueError: If the query fails
        """
        try:
            payload: dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables
            with httpx.Client(headers=self._headers, timeout=30.0) as client:
                resp = client.post(self.graphql_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            if "errors" in data and data["errors"]:
                msg = "; ".join(e.get("message", str(e)) for e in data["errors"])
                raise ValueError(f"GraphQL errors: {msg}")
            return data.get("data", data)
        except httpx.HTTPStatusError as e:
            logger.error(f"GraphQL HTTP error: {e.response.status_code} {e.response.text}")
            raise ValueError(f"GraphQL request failed: {e.response.text}") from e
        except Exception as e:
            logger.error(f"GraphQL query failed: {str(e)}")
            raise ValueError(f"GraphQL query failed: {str(e)}") from e

    async def execute_query_async(self, query: str, variables: dict | None = None) -> dict:
        """
        Execute a GraphQL query or mutation asynchronously.

        Args:
            query: The GraphQL query/mutation as string
            variables: Optional variables for the query

        Returns:
            The query result (data or response dict)

        Raises:
            ValueError: If the query fails
        """
        try:
            payload: dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables
            client = self._get_async_client()
            resp = await client.post(self.graphql_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data and data["errors"]:
                msg = "; ".join(e.get("message", str(e)) for e in data["errors"])
                raise ValueError(f"GraphQL errors: {msg}")
            return data.get("data", data)
        except httpx.HTTPStatusError as e:
            logger.error(f"GraphQL HTTP error: {e.response.status_code} {e.response.text}")
            raise ValueError(f"GraphQL request failed: {e.response.text}") from e
        except Exception as e:
            logger.error(f"GraphQL query failed: {str(e)}")
            raise ValueError(f"GraphQL query failed: {str(e)}") from e

    async def close(self) -> None:
        """Close the async client if open."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None

    async def __aenter__(self) -> "ShopifyClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def get_shopify_client(
    store_config: dict[str, Any] | None = None,
) -> ShopifyClient:
    """
    Get a configured Shopify client instance.

    Args:
        store_config: Optional store configuration dict

    Returns:
        Configured ShopifyClient instance
    """
    return ShopifyClient(store_config=store_config)
