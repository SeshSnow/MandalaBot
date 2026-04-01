"""
Firecrawl-powered web search tool for finding verified URLs by keyword.

Returns title, URL, and description metadata without scraping full page content,
keeping requests fast and token-efficient for LLM consumption.
"""

from typing import List

from firecrawl import FirecrawlApp

from nanobot.tools.decorator import tool


def _get_firecrawl_client() -> FirecrawlApp:
    from nanobot.config.mandala import MandalaConfig
    cfg = MandalaConfig()
    api_key = cfg.firecrawl_api_key
    if not api_key:
        raise RuntimeError("FIRECRAWL_API_KEY is not set")
    return FirecrawlApp(api_key=api_key)


@tool(
    description=(
        "Search the web for real URLs related to a keyword or phrase using Firecrawl. "
        "Returns an array of results with title, url, and description. "
        "Parameters: keyword (required, the search query), limit (max results, default 10)."
    )
)
async def firecrawl_web_search(keyword: str, limit: int = 10) -> dict:
    """
    Find verified URLs and metadata for a keyword via Firecrawl search.

    Returns metadata only (no full-page scrape), making it fast and cheap.
    Useful for sourcing external references, competitor research, and link building.
    """
    limit = max(1, min(50, limit))
    try:
        client = _get_firecrawl_client()
        results = client.search(
            query=keyword,
            params={
                "limit": limit,
            },
        )

        data: list = results.get("data", []) if isinstance(results, dict) else results
        verified_links: List[dict] = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            }
            for item in data
            if isinstance(item, dict)
        ]

        return {
            "keyword": keyword,
            "results": verified_links,
            "total": len(verified_links),
        }
    except Exception as e:
        return {
            "error": str(e),
            "keyword": keyword,
            "results": [],
            "total": 0,
        }
