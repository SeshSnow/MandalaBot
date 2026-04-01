---
name: marketing-research
description: Generate comprehensive marketing research using web browsing, SE Ranking data, and product context. Creates an 8-section document useful for ALL marketing channels - social media, paid ads, email, sales pages, and SEO. Tools include get_brand_context, top_selling_products, collections_and_categories, seranking_related_keywords, web_fetch, web_search, and save_research_document.
---

# Marketing Research Agent

## CRITICAL RULES

1. **NEVER STOP on tool errors**: If a tool returns `{"success": false, "error": "..."}`, this is INFORMATION, not a reason to stop. Continue with available data.
2. **ALWAYS SAVE**: You MUST call `save_research_document` at the end, even if some tools failed. An incomplete document is better than no document.
3. **NO BLOCKING**: No tool failure should prevent you from completing your task. Always proceed to the save step.

## Purpose

Generate comprehensive marketing research that informs ALL marketing channels. Use this skill as the foundation for all marketing activities - it provides the strategic context needed for ad copywriting, content creation, email sequences, and sales pages.

**When to use:**

- First skill in any marketing workflow
- When starting new campaigns or launching new products
- Annually for refresh
- Quarterly for updates

**Key Principle:** This skill DISCOVERS competitor domains during research - do not expect them as input.

---

## Prerequisites

**If NO Shop Context Available:**
If `get_brand_context` returns "Shop context not available" or similar error:

1. **DO NOT ask the user for clarification** - proceed immediately with general market research
2. Use `web_search` to discover: "popular e-commerce product categories 2024" or "trending online business niches"
3. Generate a **general market research report** about e-commerce trends and best practices
4. Save the document with a note: "General market research - no specific shop context available"
5. The user can then provide specific business details for a follow-up research

---

## Phase 1: Business & Product Context

**Objective:** Gather brand and product information from available sources.

**Steps:**

1. Call `get_brand_context` to fetch brand_name, description, primary_domain
2. Call `top_selling_products(limit=10)` for best-selling products
3. Call `collections_and_categories` for collections, product types, and tags
4. Optionally call `seranking_related_keywords` for product types to discover keywords

**Expected Output:** Brand context, product catalog, and keyword foundation.

### 1a. Brand Context (from database)

1. Call `get_brand_context` to fetch:
    - `brand_name`: Store name
    - `description`: Business description (what they sell)
    - `primary_domain`: Public domain for SE Ranking lookups

**FALLBACK:** If `get_brand_context` returns any error (including shop context unavailable):

- **DO NOT STOP** - Write "Brand context unavailable" in Section 1
- Use `web_search` for general industry terms like "common product categories for [shop name]" or "typical business in [industry if known]"
- Focus on general market research that doesn't require specific brand data
- Ask the user for a brief business description if needed: "What product category or industry should I research?"

### 1b. Product Context (from Shopify)

1. Call `top_selling_products(limit=10)` to get best-selling products
2. Call `collections_and_categories` to get:
    - Collections (product groupings)
    - Product types (categories)
    - Product tags (attributes)
3. Understand: What do they sell? Price points? Product categories?

### 1c. Focused Keywords (from SE Ranking - Optional)

For each top product type/category:

1. Call `seranking_related_keywords(keyword=product_type, source="us", limit=20)` to discover keywords
2. Aggregate keywords to understand customer search behavior
3. Skip if SE Ranking data is sparse or unavailable

---

## Phase 2: Competitive Intelligence

**Objective:** Discover and analyze competitors through web research.

**Steps:**

1. Use `web_search` for "[product category] brands" or "[industry] competitors"
2. Use SE Ranking domain competitors via `seranking_domain_overview` if primary_domain available
3. Search Facebook Ad Library for competitor discovery
4. Analyze 3-5 discovered competitors' websites and ads
5. Mine customer reviews for insights

**Expected Output:** Competitor list with messaging, offers, and ad analysis.

**Competitor Discovery (NOT provided as input)**
Competitors are discovered during research using:

1. `web_search` for "[product category] brands" or "[industry] competitors"
2. SE Ranking domain competitors via `seranking_domain_overview` (if primary_domain available)
3. Facebook Ad Library searches

For 3-5 discovered competitors:

### 2a. Website Analysis

For each competitor, use `web_fetch` to browse their website and analyze:

- **Homepage messaging**: What's their headline? What problem do they solve?
- **About page**: Brand story, mission, tone of voice
- **Product pages**: How do they describe products? What benefits emphasized?
- **Pricing**: Price points, offers, bundles, guarantees

### 2b. Facebook Ad Library Research

Search Facebook Ad Library for each competitor using `web_fetch`:

- **Ad creative**: What images/videos do they use?
- **Ad copy**: What hooks, angles, and CTAs work for them?
- **Offers**: What promotions, discounts, or lead magnets?
- URL: https://www.facebook.com/ads/library/

### 2c. Customer Review Mining

Search for reviews using `web_search` and `web_fetch` (Google, Trustpilot, Amazon if applicable):

- **Pain points**: What problems do customers mention?
- **Language**: Exact words customers use to describe the problem/solution
- **Objections**: What complaints or hesitations appear?
- **Praise**: What do customers love? What surprises them?

---

## Phase 3: Market Context

**Objective:** Understand broader market trends and factors.

**Steps:**

1. Use `web_search` for market size, growth trends
2. Identify industry challenges and opportunities
3. Note emerging competitors or trends
4. Document regulatory or seasonal factors

**Expected Output:** Market context summary with trends and opportunities.

Use `web_search` to understand:

- Market size and growth trends
- Industry challenges and opportunities
- Emerging competitors or trends
- Regulatory or seasonal factors

---

## Phase 4: Search Behavior

**Objective:** Gather SEO and keyword data for content strategy.

**Steps:**

1. If SE Ranking useful, call `seranking_domain_overview` for traffic benchmarks
2. Call `seranking_related_keywords` for customer questions/topics
3. Skip if brand is new, primarily social/paid focused, or SE Ranking data is sparse

**Expected Output:** Keyword data and SEO recommendations (if available).

If SE Ranking data is useful for this brand:

- `seranking_domain_overview` for traffic benchmarks
- `seranking_related_keywords` for customer questions/topics

Skip if: brand is new, primarily social/paid focused, or SE Ranking data is sparse.

---

## Output Format

The output must be a markdown document with the following structure:

### Section 1: Market Positioning Analysis

**Data sources**: Competitor websites, brand context, web search

- Current Position Assessment
- UVP Analysis (compare vs competitor headlines)
- Market Opportunity (white space, unaddressed pain points)

### Section 2: Competitive Landscape

**Data sources**: Competitor websites, Facebook Ad Library, customer reviews

- Competitor Matrix Table (domain, positioning, key message, strengths, weaknesses)
- Messaging Analysis per competitor
- Ad Creative Patterns (hooks, offers, CTAs)
- Competitive Weaknesses (industry-wide gaps)

### Section 3: Target Audience Research

**Data sources**: Customer reviews, competitor content, SE Ranking (optional)

- Demographics (age range, location, income, professional backgrounds)
- Psychographics (values, fears, aspirations, identity markers)
- Pain Points with ACTUAL Customer Quotes (from reviews - not paraphrased)
- Buyer Journey Mapping (awareness triggers, consideration factors, decision drivers)

### Section 4: Product-Market Fit

**Data sources**: Shopify products, competitor pricing, customer reviews

- Problem-Solution Alignment
- Market Validation Signals
- Growth Potential Assessment

### Section 5: Messaging Strategy

**Data sources**: Competitor messaging, customer reviews, ad library

- Core Messaging Themes (primary benefit, supporting benefits, proof points)
- Messaging Gaps vs Competitors (what they miss)
- Voice & Tone Recommendations (based on customer language)
- Emotional Triggers (fear-based, aspiration-based, trust-building)

### Section 6: Marketing Channels

**Data sources**: Competitor ad presence, content strategy, SE Ranking (optional)

- Paid Ads Strategy (proven angles, hook formulas, offer structures)
- Social Media Strategy (content themes, engagement patterns)
- Email Marketing Strategy (sequence ideas, subject line angles)
- SEO Content Strategy (topic clusters, content gaps - if SE Ranking available)
- Recommended Channel Mix (primary/secondary channels, budget allocation)

### Section 7: Pricing Strategy

**Data sources**: Competitor websites, product pages, customer reviews

- Market Pricing Landscape (competitor price points, common models)
- Value Perception Factors (premium justifications, worth-it factors from reviews)
- Pricing Recommendations (positioning, offer structure ideas, risk reversal)

### Section 8: Growth Strategy

**Data sources**: All gathered data synthesized

- Quick Wins (0-3 months) with specific actions and rationale
- Medium-Term (3-6 months) with specific actions
- Long-Term (6-12 months) with specific actions
- KPIs to Track (acquisition, engagement, revenue metrics)

Format:

```markdown
# Market Research Report

## 1. Market Positioning Analysis

[Content here]

## 2. Competitive Landscape

[Content here]

...
```

---

## Saving the Document

After generating the complete document, format it as markdown and save using `save_research_document`:

```python
save_research_document(
    document_type="market_research",
    content_markdown="# Market Research Report\n\n## 1. Market Positioning Analysis\n\n...(full markdown content)...",
    metadata={
        "data_sources": ["competitor_sites", "facebook_ad_library", "reviews", "seranking"],
        "competitors_analyzed": ["competitor1.com", "competitor2.com", ...]
    }
)
```

The `content_markdown` parameter should contain the complete markdown document with all 8 sections formatted for readability.

**CRITICAL: Always verify the save succeeded:**

- Check that `save_research_document` returns `{"success": true, "document_id": "..."}`
- If `success` is `false` or missing, retry the save up to 2 times
- If save still fails, report the error and DO NOT complete the task
- Never finish without confirming the document was saved successfully

---

## OUTPUT QUALITY REQUIREMENTS

Your output MUST meet ALL of the following:

1. **Source citation**: Every insight references its source (competitor site, review, ad library, SE Ranking)
2. **Quote authenticity**: Customer quotes are exact language, not paraphrased
3. **Table formatting**: Competitor matrix uses proper markdown tables
4. **Channel specificity**: Each marketing channel recommendation is specific and actionable
5. **Data acknowledgment**: Sections with sparse data include limitation notes
6. **Length**: Minimum 6 pages (approximately 3000 words) of detailed content
7. **Structure**: Uses clear H1 for title, H2 for 8 main sections, H3 for subsections
8. **Actionability**: Growth strategy includes specific actions with timeline (0-3, 3-6, 6-12 months)

---

## Error Handling

If get_brand_context returns error (including "Shop context not available"):

- **DO NOT stop** - this is a non-blocking error
- Note "Brand context unavailable" in Section 1 (Market Positioning Analysis)
- Proceed with general market research using web search only
- Use the shop domain from context if available, otherwise research general industry trends
- Request minimal brand description from user if needed (ask: "What industry/product category should I research?")

If Shopify tools fail:

- Proceed with competitor analysis only
- Note "Product data unavailable" in Product-Market Fit section

If SE Ranking data sparse:

- Skip SE Ranking sections entirely
- Note "Limited SEO data available" and focus on competitive intelligence

If web_search/web_fetch blocked:

- Try alternative search terms
- Note "Unable to access [source]" and continue with available data

If save_research_document fails:

- Retry up to 2 times with the same content
- If still failing, report: "CRITICAL: Failed to save research document. Error: {error_message}"
- Do not mark the task as complete - the document must be saved to be useful
- Document what was attempted in the final response
