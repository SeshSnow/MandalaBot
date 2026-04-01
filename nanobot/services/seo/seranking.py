"""
SE Ranking API client for nanobot.

Lightweight async client for keyword and domain research via SE Ranking API.
"""

import asyncio
import time
from typing import Any

import httpx

_KEYWORD_OPTIONAL_PARAM_MAP: dict[str, str] = {
    "volume_from": "filter[volume][from]",
    "volume_to": "filter[volume][to]",
    "relevance_from": "filter[relevance][from]",
    "difficulty_from": "filter[difficulty][from]",
    "difficulty_to": "filter[difficulty][to]",
    "competition_from": "filter[competition][from]",
    "competition_to": "filter[competition][to]",
    "keyword_count_from": "filter[keyword_count][from]",
    "keyword_count_to": "filter[keyword_count][to]",
    "characters_count_from": "filter[characters_count][from]",
    "characters_count_to": "filter[characters_count][to]",
}

_KEYWORD_PASSTHROUGH_PARAMS = {
    "limit", "offset", "sort", "sort_order", "history_trend", "intents", "serp_features",
}

_DOMAIN_KEYWORDS_OPTIONAL_PARAM_MAP: dict[str, str] = {
    "volume_from": "filter[volume][from]",
    "volume_to": "filter[volume][to]",
    "position_from": "filter[position][from]",
    "position_to": "filter[position][to]",
    "difficulty_from": "filter[difficulty][from]",
    "difficulty_to": "filter[difficulty][to]",
    "traffic_from": "filter[traffic][from]",
    "traffic_to": "filter[traffic][to]",
}

_DOMAIN_KEYWORDS_PASSTHROUGH = {
    "url", "with_subdomains", "type", "order_field", "order_type", "page", "limit",
}


def _merge_keyword_options(params: dict[str, Any], kwargs: dict[str, Any]) -> None:
    for key, value in kwargs.items():
        if value is None:
            continue
        if key in _KEYWORD_OPTIONAL_PARAM_MAP:
            params[_KEYWORD_OPTIONAL_PARAM_MAP[key]] = value
        elif key in _KEYWORD_PASSTHROUGH_PARAMS:
            if key == "history_trend":
                params[key] = "true" if value else "false"
            elif key == "intents" and isinstance(value, (list, tuple)):
                params["filter[intents]"] = ",".join(str(v) for v in value)
            elif key == "serp_features" and isinstance(value, (list, tuple)):
                params["filter[serp_features]"] = ",".join(str(v) for v in value)
            else:
                params[key] = value


def _merge_domain_keywords_options(params: dict[str, Any], kwargs: dict[str, Any]) -> None:
    for key, value in kwargs.items():
        if value is None:
            continue
        if key in _DOMAIN_KEYWORDS_OPTIONAL_PARAM_MAP:
            params[_DOMAIN_KEYWORDS_OPTIONAL_PARAM_MAP[key]] = value
        elif key in _DOMAIN_KEYWORDS_PASSTHROUGH:
            if key == "with_subdomains" and isinstance(value, bool):
                params["with_subdomains"] = 1 if value else 0
            else:
                params[key] = value


class SERankingClient:
    """Lightweight async SE Ranking API client."""

    def __init__(self) -> None:
        from nanobot.config.mandala import MandalaConfig
        cfg = MandalaConfig()
        api_key = cfg.se_ranking_api_key
        if not api_key or api_key == "YOUR_SE_RANKING_API_KEY":
            raise ValueError("SE_RANKING_API_KEY is not configured")

        self.api_key = api_key
        self.base_url = "https://api.seranking.com"
        self.max_retries = 2
        self.requests_per_second = 10
        self.retry_delay = 1.0
        self._last_request_time = 0.0
        self.min_request_interval = 1.0 / self.requests_per_second

    async def _rate_limit(self) -> None:
        current_time = time.monotonic()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
        self._last_request_time = time.monotonic()

    async def _make_request(self, method: str, endpoint: str, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Token {self.api_key}"}
        attempts = 0
        last_error: Exception | None = None

        while attempts < self.max_retries:
            try:
                await self._rate_limit()
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if data is not None:
                        response = await client.request(method=method, url=url, headers=headers, params=params, data=data)
                    else:
                        response = await client.request(method=method, url=url, headers=headers, params=params)
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else None
                if status_code == 401:
                    raise Exception(f"SE Ranking authentication failed: {str(e)}") from e
                elif status_code == 429:
                    raise Exception(f"SE Ranking rate limit exceeded: {str(e)}") from e
                last_error = e
                attempts += 1
                if attempts == self.max_retries:
                    raise Exception(f"SE Ranking API error after {attempts} attempts: {str(e)}") from last_error
                await asyncio.sleep(self.retry_delay)
            except (httpx.TimeoutException, httpx.RequestError) as e:
                last_error = e
                attempts += 1
                if attempts == self.max_retries:
                    raise Exception(f"SE Ranking request failed after {attempts} attempts: {str(e)}") from last_error
                await asyncio.sleep(self.retry_delay)

        raise last_error or RuntimeError("SE Ranking request failed")

    async def get_related_keywords(self, keyword: str, source: str = "us", **kwargs: Any) -> dict[str, Any]:
        endpoint = "/v1/keywords/related"
        params: dict[str, Any] = {
            "keyword": keyword, "source": source or "us",
            "limit": kwargs.pop("limit", 20), "offset": kwargs.pop("offset", 0),
            "sort": kwargs.pop("sort", None) or "volume",
        }
        sort_order = kwargs.pop("sort_order", None)
        if sort_order:
            params["sort_order"] = sort_order
        _merge_keyword_options(params, kwargs)
        return await self._make_request("GET", endpoint, params)

    async def get_similar_keywords(self, keyword: str, source: str = "us", **kwargs: Any) -> dict[str, Any]:
        endpoint = "/v1/keywords/similar"
        params: dict[str, Any] = {
            "keyword": keyword, "source": source or "us",
            "limit": kwargs.pop("limit", 20), "offset": kwargs.pop("offset", 0),
            "sort": kwargs.pop("sort", None) or "volume",
        }
        sort_order = kwargs.pop("sort_order", None)
        if sort_order:
            params["sort_order"] = sort_order
        _merge_keyword_options(params, kwargs)
        return await self._make_request("GET", endpoint, params)

    async def get_longtail_keywords(self, keyword: str, source: str = "us", **kwargs: Any) -> dict[str, Any]:
        endpoint = "/v1/keywords/longtail"
        params: dict[str, Any] = {
            "keyword": keyword, "source": source or "us",
            "limit": kwargs.pop("limit", 20), "offset": kwargs.pop("offset", 0),
        }
        return await self._make_request("GET", endpoint, params)

    async def get_domain_overview(self, domain: str, source: str = "us", **kwargs: Any) -> dict[str, Any]:
        endpoint = "/v1/domain/overview/db"
        params: dict[str, Any] = {"domain": domain, "source": source or "us", "with_subdomains": kwargs.pop("with_subdomains", 1)}
        url_param = kwargs.pop("url", None)
        if url_param:
            params["url"] = url_param
        return await self._make_request("GET", endpoint, params)

    async def get_domain_pages(self, target: str, scope: str, source: str = "us", type: str = "organic", order_field: str = "traffic_sum", limit: int = 10) -> dict[str, Any]:
        endpoint = "/v1/domain/pages"
        params = {"target": target, "scope": scope, "source": source or "us", "type": type, "order_field": order_field, "limit": limit}
        return await self._make_request("GET", endpoint, params)

    async def get_domain_keywords(self, domain: str, source: str = "us", **kwargs: Any) -> dict[str, Any]:
        endpoint = "/v1/domain/keywords"
        params: dict[str, Any] = {
            "domain": domain, "source": source or "us",
            "type": kwargs.pop("type", "organic"), "order_field": kwargs.pop("order_field", "traffic"),
            "limit": kwargs.pop("limit", 20),
        }
        order_type = kwargs.pop("order_type", None)
        if order_type:
            params["order_type"] = order_type
        page = kwargs.pop("page", None)
        if page is not None:
            params["page"] = page
        _merge_domain_keywords_options(params, kwargs)
        return await self._make_request("GET", endpoint, params)

    async def get_keyword_overview(self, keyword: str, source: str = "us") -> dict[str, Any]:
        endpoint = "/v1/keywords/export"
        params = {"source": source or "us"}
        data = {"keywords[]": keyword}
        raw = await self._make_request("POST", endpoint, params=params, data=data)
        if isinstance(raw, list) and len(raw) > 0:
            return raw[0]
        if isinstance(raw, dict):
            return raw
        return {"keyword": keyword, "is_data_found": False}
