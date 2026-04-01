---
name: customer-avatar
description: Create detailed customer avatars with voice bank for all marketing channels. Requires market research to exist first. Uses get_research_document, web_fetch, web_search, and save_research_document tools. Generates 2-3 avatars with ACTUAL customer quotes organized for copywriters.
---

# Customer Avatar Agent

## Purpose

Create detailed customer avatars with voice bank for all marketing channels. Use this skill after market research to develop 2-3 distinct customer personas with ACTUAL customer language. The voice bank output should be immediately usable by copywriters for ads, emails, and sales pages.

**When to use:**
- After market research is complete
- Before writing ad copy, email sequences, or sales pages
- When developing new marketing campaigns

**Key Principle:** Every quote must be ACTUAL customer language from reviews, NOT paraphrased or generated.

---

## Prerequisites

Market research must exist before generating avatars.

1. Call `get_research_document(document_type="market_research")` to check if market research exists
2. If not found, inform the user that market research must be generated first
3. Use the market research content to understand the target audience foundation

---

## Phase 1: Review Mining Deep Dive

**Objective:** Capture EXACT customer language from reviews for voice bank.

**Steps:**
1. Use `web_search` to find review sites (Amazon, Trustpilot, G2, Google Reviews, Reddit)
2. Use `web_fetch` to browse each review source
3. Extract quotes for each category:
   - Problem Awareness (before solution)
   - Emotional State (while struggling)
   - Failed Attempts (what didn't work)
   - Transformation (after solving problem)
4. Note exact source for each quote
5. Document repeated words/phrases customers use

**Expected Output:** Collection of 30+ ACTUAL customer quotes with source attribution.

### 1a. Review Sites

Use `web_search` and `web_fetch` to browse review sites for the brand or similar products:
- Amazon reviews (if applicable)
- Trustpilot, G2, Capterra (for B2B)
- Google Reviews
- Reddit discussions (r/[industry], r/[product_category])
- Facebook groups and comments
- YouTube video comments on competitor products

### 1b. Extract Voice of Customer

Capture EXACT quotes (not paraphrased) for each of these categories:
- **Problem Awareness**: How they describe the problem BEFORE finding a solution
  - Look for: "I was so frustrated that...", "The worst part was...", "I couldn't..."
- **Emotional State**: How they feel when struggling
  - Look for: "It made me feel...", "I was embarrassed that...", "I was scared..."
- **Failed Attempts**: What they tried that didn't work
  - Look for: "I tried X but...", "Nothing worked until...", "I spent money on..."
- **Transformation**: How they describe life AFTER solving the problem
  - Look for: "Now I can...", "Finally I...", "I never thought I'd..."
- **Repeated Words**: Words and phrases customers use repeatedly
  - Note exact terminology customers use to describe the problem/solution

---

## Phase 2: Avatar Development

**Objective:** Create 2-3 distinct customer avatars with demographics, psychographics, and pain points.

**Steps:**
1. Identify 2-3 distinct customer segments from review data
2. For each segment, develop detailed avatar with demographics
3. Document psychographics (values, fears, aspirations)
4. List pain points with actual customer quotes
5. Document objections and buying journey

**Expected Output:** Complete avatar profiles for 2-3 customer segments.

Create 2-3 distinct customer avatars. Each avatar should represent a different segment of the target audience.

### For Each Avatar:

#### Core Identity
- **Name**: Descriptive name that captures their essence (e.g., "Frustrated Karen", "Skeptical Steve")
- **Tagline**: One-line description of who they are

#### Demographics
- Age range
- Location (if relevant)
- Income range
- Occupation/professional background

#### Psychographics
- **Values**: What matters most to them
- **Fears**: What keeps them up at night
- **Aspirations**: What they're working toward
- **Identity Markers**: How they see themselves

#### Pain Points (with ACTUAL quotes)
3-5 pain points, each containing:
- Description of the pain point
- Intensity level (mild/moderate/severe)
- 2-4 ACTUAL customer quotes expressing this pain
- Source of quotes (e.g., "Amazon reviews", "Reddit r/skincare")

#### Goals & Desires (with ACTUAL quotes)
- Short-term goals: What do they want immediately?
- Long-term goals: What transformation do they seek?
- 2-3 ACTUAL quotes expressing these desires

#### Objections & Hesitations
- What stops them from buying?
- Past failures that make them skeptical
- Price/value concerns
- Trust issues

#### Buying Journey
- **Awareness Triggers**: What makes them realize they have a problem?
- **Consideration Factors**: What do they compare when evaluating solutions?
- **Decision Factors**: What tips them over the edge to buy?

---

## Phase 3: Voice Bank Creation

**Objective:** Create organized quote library categorized by marketing use case.

**Steps:**
1. Compile quotes into voice bank categories
2. Ensure 3-5 quotes per category minimum
3. Include source attribution for each quote
4. Organize by marketing channel use case

**Expected Output:** Voice bank with Problem Awareness, Failed Attempts, Desire Statements, Transformation, and Objections categories.

Create an organized quote library for copywriters. This is the KEY deliverable for ad writers.

### Voice Bank Categories

For each category, collect 3-5 ACTUAL customer quotes:

#### Problem Awareness
*"I'm so frustrated that..."*
- Quotes that express the problem
- Use for: Ad hooks, email subject lines, sales page openers

#### Failed Attempts
*"I've tried X but..."*
- Quotes about what didn't work
- Use for: Building empathy, showing you understand

#### Desire Statements
*"I just want to..."*
- Quotes expressing what they want
- Use for: Benefit bullets, vision sections

#### Transformation
*"Now I feel..."*
- Quotes from happy customers about the change
- Use for: Testimonials, before/after sections

#### Objections
*"But what if..."*
- Quotes expressing hesitations
- Use for: FAQ sections, objection handling

---

## Phase 4: Marketing Applications

**Objective:** Provide actionable marketing guidance for each avatar.

**Steps:**
1. Generate 3-5 hook ideas per avatar using customer language
2. Create email subject line suggestions
3. Recommend social content themes
4. Provide sales page recommendations

**Expected Output:** Actionable marketing applications for each avatar.

For each avatar, provide specific guidance on how to use the insights.

### Ad Copy Angles
- 3-5 hook ideas based on pain points (using customer language)
- Ad headline formulas using actual quotes
- Angle recommendations (fear-based, aspiration-based, curiosity)

### Email Subject Lines
- 5-10 subject line ideas using customer language
- Emotional triggers to use

### Social Content Themes
- Topics that resonate with this avatar
- Content formats that work (carousel, video, story)
- Engagement hooks

### Sales Page Recommendations
- How to open (which pain point to lead with?)
- Objection handling order
- Proof types needed (testimonials, case studies, stats)

---

## Output Format

The output must be a markdown document with the following structure:

### Avatar Profile Section

For each avatar (2-3), include:

- **Core Identity**: Name, tagline
- **Demographics**: Age range, location, income, occupation
- **Psychographics**: Values, fears, aspirations, identity markers
- **Pain Points**: 3-5 pain points with actual customer quotes and intensity
- **Goals & Desires**: Short-term and long-term goals with quotes
- **Objections & Hesitations**: What stops them from buying
- **Buying Journey**: Awareness triggers, consideration factors, decision factors

### Voice Bank Section

Organized by category with 3-5 quotes each:

- **Problem Awareness**: Quotes expressing the problem
- **Failed Attempts**: Quotes about what didn't work
- **Desire Statements**: Quotes expressing what they want
- **Transformation**: Quotes from happy customers
- **Objections**: Quotes expressing hesitations

### Marketing Applications Section

For each avatar:

- **Ad Copy Angles**: 3-5 hook ideas with customer language
- **Email Subject Lines**: 5-10 subject line ideas
- **Social Content Themes**: Topics, formats, engagement hooks
- **Sales Page Recommendations**: Opening pain point, objection handling order, proof types needed

Format:
```markdown
# Customer Avatar Report

## Avatar 1: [Name]

### Core Identity

[Content]

### Pain Points

[Content with quotes]

## Voice Bank

### Problem Awareness

[Quotes with sources]

## Marketing Applications

### Ad Copy Angles

[Content]
```


After generating the complete avatar document, format it as markdown and save using `save_research_document`:

```python
save_research_document(
    document_type="customer_avatar",
    content_markdown="# Customer Avatar Report\n\n## Avatar 1: Frustrated Karen\n\n### Core Identity\n...(full markdown content)...",
    metadata={
        "num_avatars": 3,
        "review_sources": ["amazon", "trustpilot", "reddit"],
        "quotes_collected": 45,
        "market_research_id": "uuid-of-market-research"
    }
)
```

The `content_markdown` parameter should contain the complete markdown document with all avatars and voice bank formatted for readability.

---

## OUTPUT QUALITY REQUIREMENTS

Your output MUST meet ALL of the following:

1. **Quote authenticity**: 100% of quotes are exact customer language (verify with source)
2. **Source tracking**: Every quote includes source (site name, URL, date)
3. **Minimum quotes**: Minimum 30 quotes across all voice bank categories
4. **Avatar distinctness**: 3 avatars represent clearly different segments (verify with demographics/psychographics)
5. **Quote distribution**: Each voice bank category has 3-5 quotes
6. **Marketing applicability**: Each avatar includes 3-5 specific hook ideas using customer language
7. **Copywriter readiness**: Voice bank organized by use case (ad hooks, subject lines, testimonials)
8. **Format**: Uses markdown tables for avatar profiles, formatted lists for voice bank

---

## Error Handling

If market research does not exist:
- Return error: "Market research required. Please run marketing-research skill first."

If no reviews found:
- Expand search to additional platforms (Twitter, YouTube comments, industry forums)
- If still no results, note "Limited review data available" and proceed with market research insights

If review sources require login:
- Note "Some review sources require login" and use available sources
- Document which sources were inaccessible
