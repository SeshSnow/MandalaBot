---
name: competitor-analysis
description: Deep competitor analysis for marketing differentiation. Requires market research to exist first. Analyzes competitor websites, ad creative, and messaging strategies. Uses get_research_document, web_fetch, web_search, and save_research_document tools.
---

# Competitor Analysis Agent

## Purpose

Generate deep competitor analysis to inform marketing differentiation strategies. Use this skill after completing market research to extract actionable insights for messaging, creative development, and brand positioning. This skill transforms raw competitor data into strategic recommendations.

**When to use:**

- After market research is complete
- Before developing ad creative or sales copy
- When repositioning or launching new campaigns

**Prerequisites:**

- Market research document must exist
- Competitor domains must be discovered from market research (not provided as input)

---

## Prerequisites

Market research must exist before generating competitor analysis.

1. Call `get_research_document(document_type="market_research")` to check if market research exists
2. If not found, inform the user that market research must be generated first
3. Extract competitor domains from the market research competitive_landscape section
4. Use 3-5 competitors for deep analysis

---

## Phase 1: Website Deep Dive

**Objective:** Analyze competitor websites to extract messaging, offers, and brand positioning.

**Steps:**

1. Identify 3-5 competitors from market research competitive_landscape section
2. For each competitor, use `web_fetch` to browse homepage
3. Analyze homepage for headline, key benefits, social proof, CTAs
4. Navigate to about page for brand story and voice
5. Review pricing/offer pages for bundles, guarantees, scarcity tactics

**Expected Output:** Detailed notes on messaging, offers, and brand voice for each competitor.

### Messaging Analysis

Browse the homepage, about page, and key product pages to capture:

- **Homepage Headline**: What's their main headline? What promise do they make?
- **Key Benefit Claims**: What benefits do they emphasize? (List 3-5)
- **Social Proof Approach**: How do they show credibility?
    - Testimonials (how many, what format?)
    - Logos/badges (press, certifications, partners)
    - Stats/numbers they highlight
- **CTA Language**: What's their primary call-to-action? How do they phrase it?

### Offer Structure

Analyze their pricing and offer pages:

- **Pricing Tiers**: What pricing structure do they use?
- **Bundles/Upsells**: What additional products do they push?
- **Guarantees**: What risk reversal do they offer? (money-back, free trial, etc.)
- **Scarcity/Urgency Tactics**: Do they use limited-time offers, countdown timers, stock warnings?

### Brand Voice

Observe their overall brand presentation:

- **Tone**: Professional, casual, edgy, premium, playful?
- **Personality Traits**: What 3-5 adjectives describe their brand?
- **Visual Style Notes**: Color palette, imagery style, photography approach

---

## Phase 2: Ad Creative Analysis

**Objective:** Analyze competitor ads to understand what creative approaches work in the market.

**Steps:**

1. For each competitor, use `web_fetch` to browse Facebook Ad Library
2. Analyze ad copy for hooks, angles, and CTAs
3. Document ad formats used (video, image, carousel)
4. Note landing page URLs and analyze their approach

**Expected Output:** Collection of competitor ads with analysis of creative strategies.

Use `web_fetch` to browse Facebook Ad Library for each competitor.

**URL**: https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q=[competitor_name]

For each competitor, analyze:

### Ad Copy Analysis

- **Hooks**: First line of ad copy (what grabs attention?)
    - Collect 5-10 different hooks per competitor
- **Angles**: What approach do they take?
    - Problem-focused (pain points)
    - Solution-focused (benefits)
    - Social proof (testimonials)
    - Curiosity (questions, mystery)
- **CTAs**: What action do they ask for?

### Ad Format Analysis

- **Formats Used**: Video, image, carousel, collection?
- **Video Length**: Short (15s), medium (30s), long (60s+)?
- **Image Styles**: Product-focused, lifestyle, UGC, graphic?

### Landing Page Notes

- Where do ads lead? (homepage, dedicated landing page, product page)
- What's the first thing you see on the landing page?
- How does the landing page continue the ad's story?

---

## Phase 3: Gap Analysis

**Objective:** Identify opportunities for differentiation based on competitor research.

**Steps:**

1. Synthesize findings from website and ad analysis
2. Identify messaging gaps and unaddressed pain points
3. Find white space in positioning and creative approaches
4. Document specific differentiation opportunities

**Expected Output:** Clear list of differentiation opportunities with rationale.

Based on all research, identify opportunities for differentiation.

### Messaging Gaps

Analyze what competitors are NOT saying:

- **Unaddressed Pain Points**: What customer problems are competitors ignoring?
- **Underused Emotional Triggers**: What emotions could be leveraged more?
- **Unaddressed Objections**: What concerns are competitors not handling?

### Positioning Opportunities

Identify where to differentiate:

- **Crowded Areas**: Where is everyone saying the same thing?
    - Avoid these positioning statements
- **White Space**: What positions are underserved?
    - Opportunity to own a unique angle
- **Unique Angles**: What could this brand own that no one else claims?
    - Based on their actual strengths

### Creative Opportunities

Find gaps in creative approach:

- **Unused Ad Formats**: What formats are competitors not using?
    - e.g., If no one does UGC-style content, that's an opportunity
- **Missing Content Types**: What content is missing from the space?
    - e.g., Educational content, behind-the-scenes, customer stories
- **Proof Types Lacking**: What proof could stand out?
    - e.g., If no one shows before/after, that could differentiate

---

## Phase 4: Creative Swipe File

**Objective:** Compile best examples categorized by type for reference.

**Steps:**

1. Collect best headlines across competitors
2. Document most effective hooks
3. Note standout visual approaches
4. Record compelling offer structures

**Expected Output:** Organized swipe file with categories: headlines, hooks, visuals, offers.

Compile the best examples to learn from (not copy).

### Best Headlines

- List 5-10 most compelling headlines found across competitors
- Note why they work

### Best Hooks

- List 5-10 most effective ad hooks
- Note the technique used (curiosity, pain, benefit, etc.)

### Best Visual Approaches

- Describe 3-5 standout visual styles
- Note what makes them effective

### Best Offers

- List 3-5 most compelling offer structures
- Note the psychological principles at play

---

## Output Format

The output must be a markdown document with the following structure:

### Competitor Analysis Section

For each competitor analyzed, include:

- **Competitor Name**: Domain and business overview
- **Messaging Analysis**: Homepage headline, key benefits, social proof approach, CTA language
- **Offer Structure**: Pricing tiers, bundles/upsells, guarantees, scarcity tactics
- **Brand Voice**: Tone, personality traits, visual style notes
- **Landing Page Notes**: Where ads lead, first impression, story continuation

Format:

```markdown
# Competitor Analysis Report

## Competitor 1: [Name]

### Messaging Analysis

[Content]

### Offer Structure

[Content]
```

After generating the complete analysis, format it as markdown and save using `save_research_document`:

```python
save_research_document(
    document_type="competitor_analysis",
    content_markdown="# Competitor Analysis Report\n\n## Competitor 1: [Name]\n\n### Messaging Analysis\n...(full markdown content)...",
    metadata={
        "competitors_analyzed": 5,
        "ad_library_date": "2024-01-15",
        "websites_analyzed": ["competitor1.com", "competitor2.com", ...],
        "market_research_id": "uuid-of-market-research"
    }
)
```

The `content_markdown` parameter should contain the complete markdown document with all competitor analyses and gap analysis formatted for readability.

---

## OUTPUT QUALITY REQUIREMENTS

Your output MUST meet ALL of the following:

1. **Completeness**: Analyze minimum 3, maximum 5 competitors with all sections (messaging, offers, brand voice, ads)
2. **Specificity**: Include minimum 5 actual headlines, 10 hooks, and 5 CTAs with exact copy
3. **Source Attribution**: Every claim references source (competitor name, URL, date accessed)
4. **Actionability**: Gap analysis provides minimum 5 specific positioning opportunities
5. **Organization**: Swipe file categorizes examples by type (headlines, hooks, visuals, offers)
6. **Differentiation Focus**: Each recommendation explicitly states how to differentiate from competitor
7. **Fresh Data**: All Facebook Ad Library data includes access date
8. **Format**: Uses markdown tables for competitor matrix, bullet lists for swipe file categories

---

## Error Handling

If market research does not exist:

- Call `get_research_document(document_type="market_research")` first
- If not found, return error: "Market research required. Please run marketing-research skill first."

If web_fetch fails for competitor website:

- Try alternative URL variations (www vs non-www, /about, /pricing)
- If still fails, note "Unable to analyze [competitor] website" and continue with others

If Facebook Ad Library returns no ads:

- Note "No active ads found for [competitor]" in the competitor section
- Try searching with different competitor name variations
