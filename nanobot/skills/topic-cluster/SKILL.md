---
name: topic-cluster
description: Build hub-and-spoke topic clusters for SEO from a seed keyword. Fetches brand context and SE Ranking data per pillar and per supporting keyword, then save_topic_cluster. Do not output full JSON in chat.
---

# Topic Cluster Generator

## Purpose

Build hub-and-spoke topic clusters for SEO content strategy. Use this skill to plan content around a seed keyword, identifying pillar topics and supporting articles that create a comprehensive content ecosystem.

**When to use:**
- When planning content strategy
- When building SEO content calendar
- Before generating SEO articles

**Key Principle:** Call SE Ranking per pillar and per supporting keyword - do not build cluster from seed data only.

---

## Prerequisites

Build a topic cluster for a **seed keyword** and **N** pillar topics (from request). Complete only after **save_topic_cluster** is called; do not reply with the structure as text.

---

## Workflow

**Objective:** Build complete topic cluster with pillar and supporting keywords.

**Steps:**
1. Call `get_brand_context` for brand name, description, target audience
2. Call `seranking_related_keywords(seed_keyword, source="us", limit=100, relevance_from=10)` - if thin, tweak params
3. Select N pillar keywords from seed results
4. For each pillar: call `seranking_related_keywords(pillar_keyword, ...)` - select 2-4 supporting keywords
5. For each supporting: call `seranking_related_keywords(supporting_keyword, ...)` to fill related_keywords
6. Build cluster_structure from gathered data
7. Call `save_topic_cluster(cluster_structure)` - required

**Expected Output:** Saved topic cluster structure (do not output JSON in chat).

1. **get_brand_context** — brand name, description, target audience.

2. **Seed:** `seranking_related_keywords(seed_keyword, source="us", limit=100, relevance_from=10)`. If thin, tweak params (lower `relevance_from`, higher `limit`). Optionally similar for more ideas.

3. Select **N** pillar keywords from seed results.

4. **Per pillar:** Call `seranking_related_keywords(pillar_keyword, ...)` for that pillar. If empty/thin, tweak params or try similar. Select 2–4 supporting keywords per pillar (keyword, volume, difficulty, relevance, cpc).

5. **Per supporting keyword:** Call `seranking_related_keywords(supporting_keyword, ...)` for that keyword to fill `related_keywords`. If empty/thin, tweak params or try similar.

6. Build **cluster_structure** from gathered data.

7. **save_topic_cluster(cluster_structure)** — required; API fails without it. Do not output the JSON in your reply.

Call SE Ranking **per pillar** and **per supporting keyword**; do not build from seed data only.

---

## Output Format

The output is a JSON structure saved via `save_topic_cluster` tool.

```json
{
  "seed_keyword": "<seed>",
  "topics": [
    {
      "keyword": "<pillar>",
      "volume": 5000,
      "difficulty": 40,
      "relevance": 85,
      "cpc": 1.5,
      "supporting_keywords": [
        {
          "keyword": "<supporting>",
          "volume": 1200,
          "difficulty": 25,
          "relevance": 90,
          "cpc": 0.8,
          "related_keywords": [
            { "keyword": "<related>", "volume": 300, "difficulty": 15, "relevance": 85 }
          ]
        }
      ]
    }
  ]
}
```

**Note:** Do not output JSON in chat. Only call save_topic_cluster.

---

## Saving the Document

After building cluster_structure, call save_topic_cluster (NOT save_research_document):

```python
save_topic_cluster(cluster_structure=cluster_structure)
```

**Important:**
- Do NOT output the JSON in your reply
- Only call the tool and wait for success
- After success, reply briefly (e.g., "Topic cluster saved.")

---

## OUTPUT QUALITY REQUIREMENTS

Your output MUST meet ALL of the following:

1. **Seed coverage**: Select N pillar topics as requested
2. **Pillar selection**: Pillars have reasonable volume (generally 1000+ search volume)
3. **Supporting keywords**: Each pillar has 2-4 supporting keywords
4. **Related keywords**: Each supporting keyword has 2-5 related keywords
5. **Data completeness**: All keywords include volume, difficulty, relevance, cpc fields
6. **Empty handling**: Use empty arrays and 0/null where data is missing
7. **Tool call**: Only call save_topic_cluster, never output JSON in text
8. **Brief response**: After save, reply only with confirmation (e.g., "Topic cluster saved.")

---

## Error Handling

If get_brand_context fails:
- Proceed without brand context
- Use default parameters for SE Ranking

If SE Ranking returns empty for seed keyword:
- Try alternative keywords or broaden search
- Try similar keywords endpoint
- If still empty, note "Insufficient keyword data" and proceed with best effort

If SE Ranking returns thin results for pillar:
- Lower relevance_from threshold
- Increase limit
- Try similar keywords endpoint
- Note "Limited data for [keyword]" if cannot improve

If save_topic_cluster fails:
- Check cluster_structure format matches specification
- Retry with corrected format
- Report error to user if persists
