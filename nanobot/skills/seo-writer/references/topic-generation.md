# Topic Generation Reference

Guidelines for generating article topics from keywords during keyword research.

## Process

1. **Input**: A focus keyword and related keywords from SE Ranking tools
2. **Goal**: Generate 3 compelling article topic suggestions that:
   - Target the focus keyword
   - Are distinct from each other
   - Cover different angles or intent types

## Topic Types

- **How-to guides**: "How to [do something] with [keyword]"
- **Ultimate guides**: "The Complete Guide to [keyword] in [year]"
- **List posts**: "[Number] [keyword] Tips/Strategies/Ideas"
- **Comparison**: "[Keyword] vs [Related]: Which is Better?"
- **Problem-solving**: "Fix [problem] with [keyword]"
- **Trends**: "[keyword] Trends in [year]: What to Expect"

## Requirements

- Include the focus keyword in each title
- Make titles click-worthy and specific
- Use current year (2025/2026) when appropriate
- Keep titles between 40-60 characters when possible
- Avoid generic titles like "All About [Keyword]"

## Output Format

Return a JSON array of exactly 3 topic strings:

```json
["Topic 1", "Topic 2", "Topic 3"]
```

## SERP Analysis Integration

Before generating topics:
1. Search Google for the focus keyword
2. Note the types of content ranking (guides, lists, products, etc.)
3. Identify underserved angles
4. Generate topics that fill gaps or improve on existing content
