"""
Shared helpers for SE Ranking tools.

Used by keyword and domain tools in this package.
"""

from typing import Any


def _extract_keywords_from_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract keywords with metrics from SE Ranking API response.

    Args:
        response: SE Ranking API response

    Returns:
        List of keyword dictionaries with metrics
    """
    keywords = []

    if isinstance(response, list):
        keywords = response
    elif isinstance(response, dict):
        keywords = response.get("keywords") or response.get("data") or response.get("results") or []

    if not isinstance(keywords, list):
        return []

    keyword_list = []
    for kw in keywords:
        if isinstance(kw, dict):
            keyword_text = kw.get("keyword") or kw.get("query") or kw.get("text")
            if keyword_text:
                keyword_list.append(
                    {
                        "keyword": keyword_text,
                        "volume": kw.get("volume", 0),
                        "difficulty": kw.get("difficulty", kw.get("kd", 0)),
                        "relevance": kw.get("relevance", 0),
                        "cpc": kw.get("cpc", kw.get("cost", 0)),
                        "intents": kw.get("intents", []),
                    }
                )
        elif isinstance(kw, str):
            keyword_list.append(
                {
                    "keyword": kw,
                    "volume": 0,
                    "difficulty": 0,
                    "relevance": 0,
                    "cpc": 0,
                    "intents": [],
                }
            )

    return keyword_list


def _normalize_intents(intents: list[str] | None = None) -> list[str] | None:
    """
    Normalize intents to a list of uppercase codes.
    Accepts list of strings; strips whitespace. Returns None if empty.
    """
    if not intents:
        return None
    out = [s.strip().upper() for s in intents if s and str(s).strip()]
    return out if out else None
