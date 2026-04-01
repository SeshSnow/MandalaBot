"""
Persistence helpers for topic cluster structures.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.models.topic_cluster import (
    LongTailKeyword,
    TopicCluster,
    TopicKeyword,
    TopicPage,
)


def _normalize_related_keyword(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "keyword": item.get("keyword", ""),
            "volume": item.get("volume", 0),
            "difficulty": item.get("difficulty", 0),
            "relevance": item.get("relevance", 1.0),
        }
    if isinstance(item, str) and item.strip():
        return {"keyword": item.strip(), "volume": 0, "difficulty": 0, "relevance": 1.0}
    return {"keyword": "", "volume": 0, "difficulty": 0, "relevance": 1.0}


async def save_cluster_structure_to_db(
    db: AsyncSession,
    topic_cluster: TopicCluster,
    cluster_structure: dict[str, Any],
) -> None:
    topics_data = cluster_structure.get("topics", [])

    for topic_idx, topic_data in enumerate(topics_data):
        topic_keyword_text = topic_data.get("keyword", "")

        topic_kw = TopicKeyword(
            topic_cluster_id=topic_cluster.id,
            keyword=topic_keyword_text,
            volume=int(topic_data.get("volume", 0)),
            difficulty=int(topic_data.get("difficulty", 0)),
            relevance=float(topic_data.get("relevance", 1.0)),
            cpc=float(topic_data.get("cpc")) if topic_data.get("cpc") else None,
            order_index=topic_idx,
        )
        db.add(topic_kw)
        await db.flush()

        pillar_page = TopicPage(
            topic_keyword_id=topic_kw.id,
            target_keyword=topic_keyword_text,
            is_pillar=True,
            keyword_difficulty=int(topic_data.get("difficulty", 0)),
            search_volume=int(topic_data.get("volume", 0)),
            relevance=float(topic_data.get("relevance", 1.0)),
            cpc=float(topic_data.get("cpc")) if topic_data.get("cpc") else None,
            order_index=0,
        )
        db.add(pillar_page)
        await db.flush()

        supporting_list = topic_data.get("supporting_keywords", [])
        for supp_idx, supp_data in enumerate(supporting_list):
            supporting_keyword = supp_data.get("keyword", "")
            related_list = supp_data.get("related_keywords", [])
            content_guidance = supp_data.get("content_guidance")

            supporting_page = TopicPage(
                topic_keyword_id=topic_kw.id,
                target_keyword=supporting_keyword,
                is_pillar=False,
                keyword_difficulty=int(supp_data.get("difficulty", 0)),
                search_volume=int(supp_data.get("volume", 0)),
                relevance=float(supp_data.get("relevance", 1.0)),
                cpc=float(supp_data.get("cpc")) if supp_data.get("cpc") else None,
                order_index=supp_idx + 1,
                content_guidance=content_guidance,
            )
            db.add(supporting_page)
            await db.flush()

            for lt_idx, related_kw in enumerate(related_list):
                n = _normalize_related_keyword(related_kw)
                if not n["keyword"]:
                    continue
                lt = LongTailKeyword(
                    page_id=supporting_page.id,
                    keyword=n["keyword"],
                    volume=int(n.get("volume", 0)),
                    difficulty=int(n.get("difficulty", 0)),
                    relevance=float(n.get("relevance", 1.0)),
                    order_index=lt_idx,
                )
                db.add(lt)
