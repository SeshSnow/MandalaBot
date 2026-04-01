"""Tool for fetching collections and product categories from Shopify."""

from collections import Counter

from pydantic import BaseModel, Field

from nanobot.services.shopify import ShopifyClient
from nanobot.services.shopify.graphql import GET_COLLECTIONS, GET_PRODUCT_TYPES_AND_TAGS
from nanobot.services.shopify.shop_context import get_shop_store_config
from nanobot.tools.decorator import tool


class CollectionsCategoriesQuery(BaseModel):
    """Query parameters for collections and categories."""

    collections_limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of collections to fetch (1-100)",
    )
    include_products: bool = Field(
        default=False,
        description="Include sample products from each collection",
    )
    products_per_collection: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of products to include per collection (if include_products is True)",
    )
    include_product_types: bool = Field(
        default=True,
        description="Include aggregated product types/categories from the catalog",
    )
    include_tags: bool = Field(
        default=True,
        description="Include aggregated product tags as attributes",
    )


async def _fetch_product_types_and_tags(client: ShopifyClient, max_products: int = 250) -> tuple[list[str], list[str]]:
    """
    Fetch all product types and tags from the store.

    Returns:
        Tuple of (top_product_types, top_tags)
    """
    all_types: list[str] = []
    all_tags: list[str] = []
    cursor = None
    fetched_count = 0

    while fetched_count < max_products:
        variables = {
            "first": min(250, max_products - fetched_count),
        }
        if cursor:
            variables["after"] = cursor

        result = await client.execute_query_async(GET_PRODUCT_TYPES_AND_TAGS, variables)
        products_data = result.get("products", {})

        edges = products_data.get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            product_type = node.get("productType")
            if product_type:
                all_types.append(product_type)
            tags = node.get("tags", [])
            if tags:
                all_tags.extend(tags)

        fetched_count += len(edges)

        page_info = products_data.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        if not has_next_page or fetched_count >= max_products:
            break

        cursor = page_info.get("endCursor")

    # Get top items by frequency
    type_counter = Counter(all_types)
    tag_counter = Counter(all_tags)

    top_types = [t for t, _ in type_counter.most_common(15)]
    top_tags = [t for t, _ in tag_counter.most_common(20)]

    return top_types, top_tags


@tool(
    description="Fetch collections and product categories from the Shopify store. "
    "Returns collections with their products, and aggregated product types and tags."
)
async def collections_and_categories(query: CollectionsCategoriesQuery) -> dict:
    """
    Fetch collections and product categories from Shopify.

    Returns:
        - Collections with title, description, product count, and optionally sample products
        - Product types/categories aggregated from the catalog
        - Product tags/attributes aggregated from the catalog
    """
    store_config = get_shop_store_config()
    if not store_config or not store_config.get("domain") or not store_config.get("accessToken"):
        return {
            "success": False,
            "error": (
                "Shopify store credentials are not available for this shop. "
                "Ensure (1) the chat request includes shopify_store_id, "
                "(2) the shop has completed Shopify app installation and onboarding so credentials are stored, and "
                "(3) this service uses the same DATABASE_URL as the app that stores credentials (e.g. the main backend), "
                "so the shopify_store_credentials table contains the shop's token."
            ),
            "collections": [],
            "product_types": [],
            "product_tags": [],
        }

    client = None
    try:
        client = ShopifyClient(store_config=store_config)
        result_data = {
            "success": True,
            "collections": [],
            "product_types": [],
            "product_tags": [],
        }

        # Fetch collections
        variables = {
            "first": query.collections_limit,
            "productsFirst": query.products_per_collection if query.include_products else 1,
        }

        result = await client.execute_query_async(GET_COLLECTIONS, variables)
        collections_data = result.get("collections", {})
        edges = collections_data.get("edges", [])

        collections = []
        for edge in edges:
            node = edge["node"]

            collection = {
                "id": node["id"],
                "title": node["title"],
                "handle": node["handle"],
                "description": node.get("description", ""),
                "image": node.get("image"),
                "products_count": node.get("productsCount", {}).get("count", 0),
                "updated_at": node.get("updatedAt"),
            }

            if query.include_products:
                products = []
                for p_edge in node.get("products", {}).get("edges", []):
                    p_node = p_edge["node"]
                    products.append(
                        {
                            "id": p_node["id"],
                            "title": p_node["title"],
                            "handle": p_node["handle"],
                            "product_type": p_node.get("productType"),
                            "tags": p_node.get("tags", []),
                        }
                    )
                collection["sample_products"] = products

            collections.append(collection)

        result_data["collections"] = collections
        result_data["collections_count"] = len(collections)

        # Fetch product types and tags if requested
        if query.include_product_types or query.include_tags:
            top_types, top_tags = await _fetch_product_types_and_tags(client)

            if query.include_product_types:
                result_data["product_types"] = top_types
                result_data["product_types_count"] = len(top_types)

            if query.include_tags:
                result_data["product_tags"] = top_tags
                result_data["product_tags_count"] = len(top_tags)

        return result_data

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "collections": [],
            "product_types": [],
            "product_tags": [],
        }
    finally:
        if client is not None:
            await client.close()
