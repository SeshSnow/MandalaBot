"""Sample product information tool (mock data)."""

from pydantic import BaseModel, Field

from nanobot.tools.decorator import tool


class ProductQuery(BaseModel):
    """Query for product lookup."""

    product_id: str = Field(..., description="The product ID to look up")
    include_variants: bool = Field(False, description="Include variant data")


@tool(description="Get product details from the catalog by ID. Mock data for testing.")
async def product_info(query: ProductQuery) -> dict:
    """Fetch product information (mock)."""
    return {
        "id": query.product_id,
        "title": "Sample Product",
        "vendor": "Acme",
        "variants": [{"id": "v1", "title": "Default", "price": "19.99"}] if query.include_variants else None,
    }
