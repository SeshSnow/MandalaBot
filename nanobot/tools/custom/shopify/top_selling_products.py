"""Tool for fetching top selling products from Shopify."""

from pydantic import BaseModel, Field

from nanobot.services.shopify import ShopifyClient
from nanobot.services.shopify.graphql import GET_TOP_SELLING_PRODUCTS
from nanobot.tools.decorator import tool


class TopSellingProductsQuery(BaseModel):
    """Query parameters for top selling products."""

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of top selling products to fetch (1-50)",
    )


@tool(description="Fetch products from the Shopify store sorted by lowest inventory (likely best sellers). Returns title, description, and price.")
async def top_selling_products(query: TopSellingProductsQuery) -> dict:
    """
    Fetch top selling products from Shopify.

    Returns products sorted by best selling with title, description, and price.
    """
    client = ShopifyClient()

    try:
        variables = {"first": query.limit}

        result = await client.execute_query_async(GET_TOP_SELLING_PRODUCTS, variables)

        products_data = result.get("products", {})
        edges = products_data.get("edges", [])

        products = []
        for edge in edges:
            node = edge["node"]
            price_range = node.get("priceRangeV2", {})
            min_price = price_range.get("minVariantPrice", {})
            max_price = price_range.get("maxVariantPrice", {})

            # Format price display
            if min_price.get("amount") == max_price.get("amount"):
                price = f"{min_price.get('amount')} {min_price.get('currencyCode', 'USD')}"
            else:
                price = f"{min_price.get('amount')} - {max_price.get('amount')} {min_price.get('currencyCode', 'USD')}"

            products.append(
                {
                    "title": node["title"],
                    "description": node.get("description", ""),
                    "price": price,
                }
            )

        return {
            "success": True,
            "count": len(products),
            "products": products,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "products": [],
        }
    finally:
        await client.close()
