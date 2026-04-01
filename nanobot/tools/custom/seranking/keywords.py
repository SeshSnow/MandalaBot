"""
SE Ranking keyword research tools for nanobot.

Provides tools to query SE Ranking API for related, similar, longtail keywords
and keyword overview metrics.
"""

from nanobot.services.seo.seranking import SERankingClient
from nanobot.tools.decorator import tool

from ._utils import _extract_keywords_from_response, _normalize_intents


@tool(
    description=(
        "Find related keywords for a seed keyword using SE Ranking. "
        "Returns keywords with volume, difficulty, and relevance. "
        'Parameters: keyword (required, the seed keyword), source (market code like "us" '
        'for United States, "uk" for United Kingdom, etc. Default: "us"), '
        "limit (max results, default 20), relevance_from (0-100, optional), "
        "volume_from (optional), intents (array of I/C/T/L/N codes, optional)."
    )
)
async def seranking_related_keywords(
    keyword: str,
    source: str = "us",
    limit: int = 20,
    relevance_from: int | None = None,
    volume_from: int | None = None,
    intents: list[str] | None = None,
) -> dict:
    """
    Get related keywords for a seed keyword.

    Related keywords are semantically related to the seed keyword and useful
    for content expansion and topic clustering. Use optional filters to narrow by
    relevance, volume, or search intent.
    """
    limit = max(1, min(100, limit if limit is not None else 20))
    source = source or "us"
    intents_list = _normalize_intents(intents)
    try:
        client = SERankingClient()
        response = await client.get_related_keywords(
            keyword=keyword,
            source=source,
            limit=limit,
            relevance_from=relevance_from,
            volume_from=volume_from,
            intents=intents_list,
        )
        keywords = _extract_keywords_from_response(response)
        return {
            "keywords": keywords,
            "total": len(keywords),
            "seed_keyword": keyword,
            "source": source,
        }
    except Exception as e:
        return {
            "error": str(e),
            "keywords": [],
            "total": 0,
            "seed_keyword": keyword,
        }


@tool(
    description=(
        "Find similar keywords for a seed keyword using SE Ranking. "
        "Returns keywords with volume and difficulty. "
        'Parameters: keyword (required), source (market code like "us" or "uk", default "us"), '
        "limit (default 20), volume_from (optional), difficulty_from (0-100, optional), "
        "difficulty_to (0-100, optional), intents (array of I/C/T/L/N codes, optional)."
    )
)
async def seranking_similar_keywords(
    keyword: str,
    source: str = "us",
    limit: int = 20,
    volume_from: int | None = None,
    difficulty_from: int | None = None,
    difficulty_to: int | None = None,
    intents: list[str] | None = None,
) -> dict:
    """
    Get similar keywords for a seed keyword.

    Similar keywords are variations and alternatives to the seed keyword,
    useful for finding keyword opportunities with similar search intent.
    Use optional filters to narrow by volume, difficulty, or intent.
    """
    limit = max(1, min(100, limit if limit is not None else 20))
    source = source or "us"
    intents_list = _normalize_intents(intents)
    try:
        client = SERankingClient()
        response = await client.get_similar_keywords(
            keyword=keyword,
            source=source,
            limit=limit,
            volume_from=volume_from,
            difficulty_from=difficulty_from,
            difficulty_to=difficulty_to,
            intents=intents_list,
        )
        keywords = _extract_keywords_from_response(response)
        return {
            "keywords": keywords,
            "total": len(keywords),
            "seed_keyword": keyword,
            "source": source,
        }
    except Exception as e:
        return {
            "error": str(e),
            "keywords": [],
            "total": 0,
            "seed_keyword": keyword,
        }


@tool(
    description=(
        "Find long-tail keyword variations for a seed keyword using SE Ranking. "
        "Returns a list of long-tail keyword phrases. "
        'Parameters: keyword (required), source (market code like "us" or "uk", '
        'default "us"), limit (default 20).'
    )
)
async def seranking_longtail_keywords(keyword: str, source: str = "us", limit: int = 20) -> dict:
    """
    Get long-tail keywords for a seed keyword.

    Long-tail keywords are longer, more specific keyword phrases that typically
    have lower search volume but higher conversion potential and less competition.
    """
    limit = max(1, min(100, limit if limit is not None else 20))
    source = source or "us"
    try:
        client = SERankingClient()
        response = await client.get_longtail_keywords(keyword=keyword, source=source, limit=limit)

        # Longtail endpoint returns keywords as strings, not objects
        keywords_raw = []
        if isinstance(response, list):
            keywords_raw = response
        elif isinstance(response, dict):
            keywords_raw = response.get("keywords") or response.get("data") or []

        total = response.get("total", len(keywords_raw)) if isinstance(response, dict) else len(keywords_raw)

        # Extract keyword strings
        keywords = []
        for kw in keywords_raw:
            if isinstance(kw, str):
                keywords.append(kw)
            elif isinstance(kw, dict):
                keyword_text = kw.get("keyword") or kw.get("query") or kw.get("text")
                if keyword_text:
                    keywords.append(keyword_text)

        return {"keywords": keywords, "total": total, "seed_keyword": keyword, "source": source}
    except Exception as e:
        return {"error": str(e), "keywords": [], "total": 0, "seed_keyword": keyword}


@tool(
    description=(
        "Get keyword overview metrics for a single keyword using SE Ranking. "
        "Returns volume, CPC, difficulty, competition, and optional history_trend "
        "(monthly search volume)."
    )
)
async def seranking_keyword_overview(
    keyword: str,
    source: str = "us",
) -> dict:
    """
    Get keyword overview and metrics for a single keyword.

    Returns SE Ranking metrics: search volume, CPC, competition, difficulty,
    and historical search volume trend. Similar to domain overview but for a keyword.
    """
    source = source or "us"
    try:
        client = SERankingClient()
        response = await client.get_keyword_overview(keyword=keyword, source=source)
        return {"keyword": keyword, "source": source, "data": response}
    except Exception as e:
        return {"error": str(e), "keyword": keyword}
