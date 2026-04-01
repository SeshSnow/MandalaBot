"""
Tool for saving a topic cluster structure from the agent to the database.

Used when the agent has built a full hub-and-spoke structure (seed_keyword,
pillar topics, supporting keywords, related/long-tail keywords) and persists it
via the request-scoped context set by the topic-clusters API.
"""

import json
from typing import Any

from loguru import logger

from nanobot.db.models.topic_cluster import TopicCluster
from nanobot.services.seo.topic_cluster_context import get_topic_cluster_request_context
from nanobot.services.seo.topic_cluster_persistence import save_cluster_structure_to_db
from nanobot.tools.decorator import tool


def _validate_cluster_structure(structure: dict[str, Any]) -> str | None:
    """
    Validate minimal shape of cluster structure. Returns error message or None if valid.

    Expected: seed_keyword (str), topics (list of dicts with keyword, supporting_keywords, etc.)
    """
    if not isinstance(structure, dict):
        return "cluster_structure must be a JSON object"
    if "seed_keyword" not in structure or not isinstance(structure["seed_keyword"], str):
        return "cluster_structure must have a string 'seed_keyword'"
    topics = structure.get("topics")
    if not isinstance(topics, list):
        return "cluster_structure must have 'topics' as a list"
    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            return f"topic at index {i} must be an object"
        if "keyword" not in t or not isinstance(t.get("keyword"), str):
            return f"topic at index {i} must have a string 'keyword'"
        supp = t.get("supporting_keywords", [])
        if not isinstance(supp, list):
            return f"topic at index {i} must have 'supporting_keywords' as a list"
        for j, s in enumerate(supp):
            if not isinstance(s, dict):
                return f"supporting_keyword at topic {i} index {j} must be an object"
            if "keyword" not in s:
                return f"supporting_keyword at topic {i} index {j} must have 'keyword'"
            rel = s.get("related_keywords", [])
            if not isinstance(rel, list):
                return f"supporting_keyword at topic {i} index {j} must have 'related_keywords' as a list"
    return None


@tool(
    description="Save the completed topic cluster structure to the database. "
    "REQUIRED final step in topic cluster generation: you MUST call this after building the structure; "
    "the API will fail if you do not. Call once with the full structure: seed_keyword (string) and topics (array). "
    "Each topic has: keyword (string), volume (number), difficulty (number), relevance (number), "
    "cpc (number or null), supporting_keywords (array). Each supporting keyword has: keyword, volume, "
    "difficulty, relevance, cpc, related_keywords (array of objects with keyword, volume, difficulty, relevance). "
    "Only call this from the topic cluster generation flow when the API has set the context. "
    "IMPORTANT: Pass cluster_structure as a JSON object (with seed_keyword and topics), NOT as a string—"
    "passing a string can truncate and fail."
)
async def save_topic_cluster(cluster_structure: dict[str, Any]) -> dict[str, Any]:
    """
    Persist the topic cluster structure using request-scoped context (brand_id, db, brand_context).

    The topic-clusters API sets the context before invoking the agent. This tool creates the
    TopicCluster row and calls save_cluster_structure_to_db. Returns cluster_id and structure
    so the API can emit the SSE event.

    Args:
        cluster_structure: Dict with seed_keyword and topics (each with supporting_keywords,
            each supporting with related_keywords). Metrics (volume, difficulty, relevance, cpc)
            are optional and default to 0 or null. Must be passed as an object, not a JSON string.

    Returns:
        Dict with success, cluster_id (str), and cluster_structure on success;
        dict with success False and error (str) on failure.
    """
    # Handle case where agent passes a JSON string instead of dict
    if isinstance(cluster_structure, str):
        try:
            cluster_structure = json.loads(cluster_structure)
            logger.debug("Parsed cluster_structure from JSON string")
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse cluster_structure as JSON: %s", e)
            msg = str(e)
            # Detect likely truncation (parse error near end of string)
            if "Expecting" in msg and getattr(e, "pos", None) is not None and e.pos > 500:
                return {
                    "success": False,
                    "error": (
                        "The cluster_structure JSON was truncated (invalid at position "
                        f"{e.pos}). Pass cluster_structure as a JSON object, not a string."
                    ),
                }
            return {"success": False, "error": f"Invalid JSON: {msg}"}

    err = _validate_cluster_structure(cluster_structure)
    if err:
        logger.warning(f"save_topic_cluster validation failed: {err}")
        logger.debug(f"Invalid cluster_structure received: {cluster_structure}")
        return {"success": False, "error": err}

    ctx = get_topic_cluster_request_context()
    if not ctx:
        return {
            "success": False,
            "error": "Topic cluster request context not set. This tool must be called from the topic cluster generation API.",
        }

    try:
        topic_cluster = TopicCluster(
            brand_id=ctx.brand_id,
            seed_keyword=cluster_structure["seed_keyword"],
        )
        ctx.db.add(topic_cluster)
        await ctx.db.flush()

        await save_cluster_structure_to_db(
            db=ctx.db,
            topic_cluster=topic_cluster,
            cluster_structure=cluster_structure,
        )
        await ctx.db.flush()

        ctx.saved_cluster_id = str(topic_cluster.id)
        ctx.saved_cluster_structure = cluster_structure

        return {
            "success": True,
            "cluster_id": str(topic_cluster.id),
            "cluster_structure": cluster_structure,
        }
    except Exception as e:
        logger.exception("save_topic_cluster failed: %s", e)
        return {"success": False, "error": str(e)}
