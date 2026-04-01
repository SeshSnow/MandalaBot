---
name: seo-writer
description: Create SEO-optimized blog content—titles with abstracts, outlines, and full articles in markdown. Use when the user or workflow needs (1) SEO title + abstract + key points generation, (2) an article outline from a title/abstract, or (3) a full 1500–2000 word article from an outline. Integrates with SE Ranking keyword tools, brand context, and optional product catalog. Follows E-E-A-T, AEO (Answer Engine Optimization), and humanization guidelines.
---

# SEO Writer

Two phases: **Phase 1** (title + abstract) → **Phase 2** (outline + article). Before generating content, perform SERP analysis and competitor research to understand top-ranking content.

Create SEO-optimized blog content in a two-phase workflow: title/abstract → outline + full article. Use this skill when generating blog content that ranks well in search engines and AI answer engines.

**When to use:**
- When user requests blog content generation
- As part of content marketing workflow
- When SEO-optimized articles are needed

**Key Principle:** Always produce the final deliverable directly. Do not delegate to `llm_completion`.

---

## Prerequisites

Two phases: **title + abstract** → **outline + article**. Before generating content, call SE Ranking tools (`seranking_related_keywords`, `seranking_similar_keywords`, `seranking_keyword_overview`) for keyword data. Obtain brand info, audience, and voice from the user or conversation context.

**Phased usage:** The workflow may call you once per phase. When the user says "Phase 1 only", output **only** title and abstract. When the user says "Phase 2 only", output **only** the outline and article. No code blocks unless requested, no extra commentary.

## SERP Analysis & Competitor Research

Before generating any content, analyze the search results for the target keyword:

1. **Call `firecrawl_web_search`** with the focus keyword and limit 10 to get top-ranking URLs and metadata (title, url, description). Use these results for SERP/competitor research.
2. **Analyze competitor content**: Note the structure, topics covered, word count, and unique angles from the returned titles and descriptions
3. **Identify gaps**: Find angles not covered by competitors that you can improve upon
4. **Use SE Ranking tools**: Call `seranking_related_keywords`, `seranking_similar_keywords`, `seranking_keyword_overview` for keyword data

Incorporate these insights into your title, abstract, outline, and article to create content that outperforms existing results.

## Phase 1: Title + Abstract

Generate **one** title and one 2–3 sentence abstract.

- Perform SERP analysis and competitor research first.
- Call SE Ranking tools for keyword/competitor data.
- If a focus keyword is given, it **must** appear in the title.
- Requirements: click-worthy, specific, 40–60 chars, current year only, incorporates SE Ranking keywords.
- When asked for "title and abstract only": put the title on the first line, then a blank line, then the abstract. Nothing else.

## Phase 2: Outline + Article

Generate both the outline and full article in a single response. Output outline first, then a blank line, then the article body.

- **Outline**: raw markdown starting with `#`, 4–8 H2s → 2–4 H3s per H2. Cover all key points.
- **Article**: 1500–2000 words, raw markdown, no H1 in body (start with H2).
- Use chosen title, abstract, key points, brand voice, `shop_domain`, SERP analysis insights, and SE Ranking keyword data.
- Follow the **Outline and article rules (reference)** section in context for formatting, links, product integration, E-E-A-T, AEO, and humanization rules.
- 3–5 external links (primary sources, descriptive anchors). Store links use `https://{shop_domain}/products/{handle}` only.
- If product catalog provided: 3–8 relevant products, images with alt text, natural "Buy Now" links.
- When asked for "outline only": output only the outline markdown, starting with `#`. No code fences, no preamble.
- When asked for "article only": output only the article body markdown—no frontmatter, code blocks, or commentary.

---

## Saving the Document

The seo-writer skill outputs content directly to the conversation. If storing in a document system is needed:

```python
# Not typically used - content is output directly
# For reference if document storage is added:
save_research_document(
    document_type="seo_content",
    content_markdown="# [Title]\n\n[Article content]...",
    metadata={
        "phase": "article",
        "word_count": 1800,
        "keyword": "target-keyword"
    }
)
```

---

## OUTPUT QUALITY REQUIREMENTS

Your output MUST meet ALL of the following:

1. **Phase compliance**: Output only the requested phase (title only, outline only, or article only)
2. **Keyword inclusion**: Focus keyword appears in title (Phase 1)
3. **Title format**: 40-60 characters, click-worthy, includes current year
4. **Abstract length**: 2-3 sentences, 50-100 words
5. **Outline structure**: H1 → 4-8 H2s → 2-4 H3s per H2
6. **Article length**: 1500-2000 words total
7. **H2/H3 compliance**: No H1 in article body, starts with H2
8. **External links**: 3-5 primary source links with descriptive anchors
9. **Product integration**: If catalog provided, 3-8 relevant products with images and links
10. **E-E-A-T**: Includes specific data, citations, and actionable content
11. **AEO compliance**: Answer-first structure, question-style headings where natural
12. **Humanization**: No banned phrases, varied sentence structure, conversational tone

---

## Error Handling

If SE Ranking tools fail:
- Proceed without keyword data if necessary
- Use best judgment for keyword placement

If product catalog unavailable:
- Skip product integration sections
- Note "Product catalog not provided" if relevant

If brand context unavailable:
- Request brand voice/audience from user
- Proceed with general best practices

If word count below minimum:
- Expand sections with additional examples, data, or explanations
- Under 1500 words is rejected
