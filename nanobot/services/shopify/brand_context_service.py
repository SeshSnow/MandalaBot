"""
Service for automatically generating brand context from Shopify product data.
Fetches product tags and types, processes them, and generates brand context configuration.
"""

from collections import Counter
from typing import Any

from loguru import logger

from nanobot.services.shopify.graphql import GET_PRODUCT_TAGS, GET_PRODUCT_TYPES
from nanobot.services.shopify.shopify_client import ShopifyClient


class BrandContextService:
    """
    Service for generating brand context from Shopify product data.
    """

    @staticmethod
    def fetch_all_product_tags(shopify_client: ShopifyClient, max_products: int = 250) -> list[str]:
        """
        Fetch all product tags from Shopify store.

        Args:
            shopify_client: Initialized Shopify client
            max_products: Maximum number of products to fetch (default: 250)

        Returns:
            List of all product tags (with duplicates for frequency counting)
        """
        all_tags = []
        cursor = None
        fetched_count = 0

        try:
            while fetched_count < max_products:
                variables = {
                    "first": min(250, max_products - fetched_count),
                }
                if cursor:
                    variables["after"] = cursor

                result = shopify_client.execute_query(GET_PRODUCT_TAGS, variables)
                products_data = result.get("products", {})

                edges = products_data.get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    tags = node.get("tags", [])
                    if tags:
                        all_tags.extend(tags)

                fetched_count += len(edges)

                page_info = products_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                if not has_next_page or fetched_count >= max_products:
                    break

                cursor = page_info.get("endCursor")

            logger.info(f"Fetched {len(all_tags)} tags from {fetched_count} products")
            return all_tags

        except Exception as e:
            logger.error(f"Error fetching product tags: {str(e)}")
            raise

    @staticmethod
    def fetch_all_product_types(shopify_client: ShopifyClient, max_products: int = 250) -> list[str]:
        """
        Fetch all product types from Shopify store.

        Args:
            shopify_client: Initialized Shopify client
            max_products: Maximum number of products to fetch (default: 250)

        Returns:
            List of all product types (with duplicates for frequency counting)
        """
        all_types = []
        cursor = None
        fetched_count = 0

        try:
            while fetched_count < max_products:
                variables = {
                    "first": min(250, max_products - fetched_count),
                }
                if cursor:
                    variables["after"] = cursor

                result = shopify_client.execute_query(GET_PRODUCT_TYPES, variables)
                products_data = result.get("products", {})

                edges = products_data.get("edges", [])
                for edge in edges:
                    node = edge.get("node", {})
                    product_type = node.get("productType")
                    if product_type:
                        all_types.append(product_type)

                fetched_count += len(edges)

                page_info = products_data.get("pageInfo", {})
                has_next_page = page_info.get("hasNextPage", False)
                if not has_next_page or fetched_count >= max_products:
                    break

                cursor = page_info.get("endCursor")

            logger.info(f"Fetched {len(all_types)} product types from {fetched_count} products")
            return all_types

        except Exception as e:
            logger.error(f"Error fetching product types: {str(e)}")
            raise

    @staticmethod
    def get_top_tags(tags: list[str], top_n: int = 8) -> list[str]:
        """Get top N most frequent tags."""
        if not tags:
            return []
        tag_counter = Counter(tags)
        return [tag for tag, _ in tag_counter.most_common(top_n)]

    @staticmethod
    def get_top_product_types(product_types: list[str], top_n: int = 10) -> list[str]:
        """Get top N most frequent product types."""
        if not product_types:
            return []
        type_counter = Counter(product_types)
        return [ptype for ptype, _ in type_counter.most_common(top_n)]

    @staticmethod
    def generate_brand_context(shopify_client: ShopifyClient) -> dict[str, Any]:
        """
        Generate brand context configuration from Shopify product data.

        Args:
            shopify_client: Initialized Shopify client

        Returns:
            Dictionary with product_categories (list) and product_attributes (list)
        """
        try:
            all_tags = BrandContextService.fetch_all_product_tags(shopify_client)
            all_types = BrandContextService.fetch_all_product_types(shopify_client)

            top_tags = BrandContextService.get_top_tags(all_tags, top_n=8)
            top_types = BrandContextService.get_top_product_types(all_types, top_n=10)

            context_config = {
                "product_categories": top_types,
                "product_attributes": top_tags,
            }

            logger.info(f"Generated brand context: {len(top_types)} categories, {len(top_tags)} attributes")
            return context_config

        except Exception as e:
            logger.error(f"Error generating brand context: {str(e)}")
            raise
