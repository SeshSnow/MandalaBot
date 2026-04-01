"""
Topic Cluster Service for generating topic clusters with agentic pillar selection.

Implements Hub and Spoke algorithm with LLM-driven pillar keyword selection
instead of rigid rule-based classification.
"""

import json
import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.topic_cluster import TopicCluster
from nanobot.services.seo.seranking import SERankingClient


def _extract_keywords_with_metrics(response: Any) -> list[dict[str, Any]]:
    keywords_raw: list = []
    if isinstance(response, list):
        keywords_raw = response
    elif isinstance(response, dict):
        keywords_raw = response.get("keywords") or response.get("data") or response.get("results") or []

    result: list[dict[str, Any]] = []
    for kw in keywords_raw:
        if isinstance(kw, dict):
            keyword_text = kw.get("keyword") or kw.get("query") or kw.get("text")
            if keyword_text:
                result.append(
                    {
                        "keyword": keyword_text,
                        "volume": kw.get("volume", 0),
                        "difficulty": kw.get("difficulty", kw.get("kd", 0)),
                        "relevance": kw.get("relevance", 1.0),
                        "cpc": kw.get("cpc", kw.get("cost", 0)),
                        "intents": kw.get("intents", []),
                    }
                )
        elif isinstance(kw, str):
            result.append(
                {
                    "keyword": kw,
                    "volume": 0,
                    "difficulty": 0,
                    "relevance": 1.0,
                    "cpc": 0,
                    "intents": [],
                }
            )
    return result


class TopicClusterService:
    """
    Async service for generating topic clusters with agentic pillar selection.

    Uses SERankingClient for keyword discovery and OpenRouter for LLM-based
    pillar keyword selection.
    """

    def __init__(self) -> None:
        self._se_client: SERankingClient | None = None

    def _get_se_client(self) -> SERankingClient:
        if self._se_client is None:
            self._se_client = SERankingClient()
        return self._se_client

    async def check_domain_authority(self, domain: str, source: str = "us") -> dict[str, Any] | None:
        try:
            client = self._get_se_client()
            return await client.get_domain_overview(domain=domain, source=source)
        except Exception as e:
            logger.warning(f"Failed to get domain overview for {domain}: {e}")
            return None

    async def check_cannibalization(self, domain: str, keyword: str, source: str = "us") -> dict[str, Any]:
        try:
            client = self._get_se_client()
            response = await client.get_domain_keywords(domain=domain, source=source, limit=100)
            keywords = _extract_keywords_with_metrics(response)
            keyword_lower = keyword.lower()
            for i, kw in enumerate(keywords):
                if kw.get("keyword", "").lower() == keyword_lower:
                    return {"exists": True, "position": i + 1}
            return {"exists": False, "position": None}
        except Exception as e:
            logger.warning(f"Failed to check cannibalization for {keyword}: {e}")
            return {"exists": False, "position": None}

    async def check_seed_keyword_overlap(
        self,
        brand_id: UUID,
        seed_keyword: str,
        db: AsyncSession,
    ) -> TopicCluster | None:
        result = await db.execute(
            select(TopicCluster).where(
                TopicCluster.brand_id == brand_id,
                func.lower(TopicCluster.seed_keyword) == func.lower(seed_keyword),
            )
        )
        return result.scalar_one_or_none()

    async def fetch_pillar_candidates(self, seed_keyword: str, source: str = "us", limit: int = 100) -> list[dict[str, Any]]:
        client = self._get_se_client()
        try:
            response = await client.get_related_keywords(keyword=seed_keyword, source=source, limit=limit)
            keywords = _extract_keywords_with_metrics(response)
            keywords = [kw for kw in keywords if kw.get("relevance", 0) >= 10]

            if keywords and len(keywords) >= 3:
                return keywords[:limit]

            response = await client.get_similar_keywords(keyword=seed_keyword, source=source, limit=limit)
            similar = _extract_keywords_with_metrics(response)
            similar.sort(key=lambda x: (x.get("volume", 0), x.get("relevance", 0)), reverse=True)
            return similar[:limit]
        except Exception as e:
            logger.warning(f"Failed to fetch pillar candidates for {seed_keyword}: {e}")
            return []

    async def select_pillars_agentic(
        self,
        candidates: list[dict[str, Any]],
        seed_keyword: str,
        brand_context: dict[str, Any],
        limit: int = 4,
    ) -> list[str]:
        if not candidates:
            return []

        from nanobot.config.mandala import MandalaConfig
        cfg = MandalaConfig()
        api_key = cfg.openrouter_api_key
        model = cfg.default_model or "moonshotai/kimi-k2.5"

        if not api_key:
            logger.warning("OpenRouter API key not set; using fallback (top by volume)")
            sorted_candidates = sorted(
                candidates,
                key=lambda x: (x.get("volume", 0), x.get("relevance", 0)),
                reverse=True,
            )
            return [kw["keyword"] for kw in sorted_candidates[:limit]]

        candidates_str = json.dumps(
            [
                {
                    "keyword": kw.get("keyword", ""),
                    "volume": kw.get("volume", 0),
                    "difficulty": kw.get("difficulty", 0),
                    "relevance": kw.get("relevance", 1.0),
                }
                for kw in candidates[:50]
            ],
            indent=2,
        )

        brand_name = brand_context.get("brand_name", "Unknown brand")
        description = brand_context.get("description", "")
        target_audience = brand_context.get("target_audience", "")

        system = (
            "You are an SEO expert. Return ONLY a JSON array of exactly N keyword strings, "
            "ordered by priority (best pillar topics first). No markdown, no explanation."
        )
        user = f"""Seed keyword: "{seed_keyword}"
Brand: {brand_name}
Description: {description}
Target audience: {target_audience or "Not specified"}

Candidates (keyword, volume, difficulty, relevance):
{candidates_str}

Select the best {limit} pillar keywords that are:
1. Semantically diverse
2. Relevant to the seed keyword
3. Commercially valuable
4. Good fit for the brand

Return a JSON array of exactly {limit} keyword strings, e.g. ["keyword1", "keyword2", ...]"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://nanobot-backend.local",
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning(f"LLM pillar selection failed: {e}; using fallback")
            sorted_candidates = sorted(
                candidates,
                key=lambda x: (x.get("volume", 0), x.get("relevance", 0)),
                reverse=True,
            )
            return [kw["keyword"] for kw in sorted_candidates[:limit]]

        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "[]")

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                selected = [str(k) for k in parsed if k][:limit]
            elif isinstance(parsed, dict):
                keys = ["pillar_keywords", "keywords", "selected"]
                for k in keys:
                    if k in parsed and isinstance(parsed[k], list):
                        selected = [str(x) for x in parsed[k] if x][:limit]
                        break
                else:
                    selected = []
            else:
                selected = []

            if selected:
                return selected
        except json.JSONDecodeError:
            match = re.search(r"\[.*?\]", content, re.DOTALL)
            if match:
                try:
                    selected = json.loads(match.group())
                    return [str(k) for k in selected if k][:limit]
                except json.JSONDecodeError:
                    pass

        sorted_candidates = sorted(
            candidates,
            key=lambda x: (x.get("volume", 0), x.get("relevance", 0)),
            reverse=True,
        )
        return [kw["keyword"] for kw in sorted_candidates[:limit]]

    async def fetch_supporting_keywords(
        self,
        pillar_keyword: str,
        source: str = "us",
        limit: int = 4,
        excluded: set[str] | None = None,
        difficulty_max: int = 50,
        volume_min: int = 500,
    ) -> list[dict[str, Any]]:
        client = self._get_se_client()
        excluded_lower = {k.lower() for k in (excluded or set())}

        try:
            response = await client.get_similar_keywords(keyword=pillar_keyword, source=source, limit=100)
            raw = _extract_keywords_with_metrics(response)

            filtered = [
                kw
                for kw in raw
                if kw.get("keyword", "").lower() not in excluded_lower
                and kw.get("difficulty", 100) <= difficulty_max
                and kw.get("volume", 0) >= volume_min
            ]

            if not filtered:
                filtered = [kw for kw in raw if kw.get("keyword", "").lower() not in excluded_lower][: limit * 2]

            return filtered[:limit]
        except Exception as e:
            logger.warning(f"Failed to fetch supporting keywords for {pillar_keyword}: {e}")
            return []

    async def fetch_longtail(
        self,
        supporting_keyword: str,
        source: str = "us",
        limit: int = 10,
        excluded: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        client = self._get_se_client()
        excluded_lower = {k.lower() for k in (excluded or set())}

        try:
            response = await client.get_similar_keywords(keyword=supporting_keyword, source=source, limit=limit * 2)
            raw = _extract_keywords_with_metrics(response)

            filtered = [
                kw
                for kw in raw
                if kw.get("keyword", "").lower() not in excluded_lower and kw.get("keyword", "").lower() != supporting_keyword.lower()
            ]
            return filtered[:limit]
        except Exception as e:
            logger.warning(f"Failed to fetch longtail for {supporting_keyword}: {e}")
            return []

    async def generate_complete_topic_cluster_structure(
        self,
        brand_id: UUID,
        seed_keyword: str,
        brand_context: dict[str, Any],
        source: str = "us",
        limit: int = 4,
        db: AsyncSession | None = None,
        progress_callback: Callable[[str, str | None, int | None], None] | None = None,
    ) -> dict[str, Any]:
        def _progress(msg: str, step: str | None = None, pct: int | None = None) -> None:
            if progress_callback:
                try:
                    progress_callback(msg, step, pct)
                except Exception:
                    pass

        _progress("Step 1: Discovering pillar topics...", "discovery", 10)

        candidates = await self.fetch_pillar_candidates(seed_keyword, source, limit=100)
        if not candidates:
            return {"seed_keyword": seed_keyword, "topics": []}

        _progress("Step 2: Selecting pillar keywords (LLM)...", "agentic", 25)

        selected_keywords = await self.select_pillars_agentic(candidates, seed_keyword, brand_context, limit)

        pillar_keywords: list[dict[str, Any]] = []
        seen = set()
        for kw in candidates:
            k = kw.get("keyword", "").lower()
            if k in seen:
                continue
            if k in {s.lower() for s in selected_keywords}:
                seen.add(k)
                pillar_keywords.append(kw)
            if len(pillar_keywords) >= limit:
                break

        if len(pillar_keywords) < limit:
            for kw in candidates:
                k = kw.get("keyword", "").lower()
                if k not in seen:
                    seen.add(k)
                    pillar_keywords.append(kw)
                if len(pillar_keywords) >= limit:
                    break

        pillar_keywords = pillar_keywords[:limit]
        existing_topic_keywords = [kw.get("keyword", "") for kw in pillar_keywords if kw.get("keyword")]
        used_supporting: set[str] = set()
        topics: list[dict[str, Any]] = []
        total = len(pillar_keywords)

        for idx, pillar_kw in enumerate(pillar_keywords):
            pillar_keyword = pillar_kw.get("keyword", "")
            if not pillar_keyword:
                continue

            _progress(
                f"Processing pillar {idx + 1}/{total}: '{pillar_keyword}'...",
                "expand",
                40 + int((idx / total) * 30) if total > 0 else 40,
            )

            excluded_supp = set(existing_topic_keywords) | used_supporting
            supporting_list = await self.fetch_supporting_keywords(pillar_keyword, source, limit=4, excluded=excluded_supp)

            supporting_keywords: list[dict[str, Any]] = []
            for supp_kw in supporting_list[:4]:
                supp_keyword = supp_kw.get("keyword", "")
                if not supp_keyword:
                    continue
                used_supporting.add(supp_keyword.lower())

                excluded_lt = excluded_supp | {supp_keyword.lower()}
                related = await self.fetch_longtail(supp_keyword, source, limit=10, excluded=excluded_lt)

                supporting_keywords.append(
                    {
                        "keyword": supp_keyword,
                        "volume": supp_kw.get("volume", 0),
                        "difficulty": supp_kw.get("difficulty", 0),
                        "relevance": supp_kw.get("relevance", 1.0),
                        "cpc": supp_kw.get("cpc"),
                        "related_keywords": related,
                        "content_guidance": None,
                    }
                )

            topics.append(
                {
                    "keyword": pillar_keyword,
                    "volume": pillar_kw.get("volume", 0),
                    "difficulty": pillar_kw.get("difficulty", 0),
                    "relevance": pillar_kw.get("relevance", 1.0),
                    "cpc": pillar_kw.get("cpc"),
                    "supporting_keywords": supporting_keywords,
                }
            )

        _progress("Topic cluster structure complete.", "complete", 95)

        return {"seed_keyword": seed_keyword, "topics": topics}
