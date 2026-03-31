---
name: research
description: Deep web research with scratch pad. Searches multiple sources, saves findings to workspace, returns concise summary. Use when you need to research a topic thoroughly without filling the conversation context.
metadata: {"openclaw": {"requires": {"bins": []}, "always": false}}
---

# Research

## Purpose

Conduct thorough web research on a topic while keeping conversation context lean. Raw fetched content stays in scratch files, only summaries enter the conversation.

## When to Use

- Researching a topic that requires multiple sources
- Competitor analysis requiring deep web research
- Market research, trend analysis, industry data gathering
- Any time you'd otherwise call web_fetch 5+ times

## Input

- `topic`: What to research (string)
- `sources` (optional): Specific URLs to fetch
- `depth`: "quick" (3 sources), "standard" (5 sources), "deep" (10 sources)

## Workflow

1. Search the web for the topic using `web_search`
2. For each relevant result, fetch the page using `web_fetch`
3. Extract key data points from each source
4. Write all findings to `scratch/research/{topic-slug}.md` using `write_file`
5. Return a concise summary (5-10 bullet points) to the agent
6. Raw content stays in the scratch file — never in conversation

## Scratch File Format

```markdown
# Research: {topic}
Date: {date}
Sources: {count}

## Source 1: {title}
URL: {url}
Key findings:
- Finding 1
- Finding 2

## Source 2: {title}
...

## Summary
- Bullet point 1
- Bullet point 2
```

## Output

Return to agent:
- 5-10 bullet point summary
- Source count
- Scratch file path (for later reference)

Do NOT return raw page content in the response. Only the summary.

## Following Up

To read detailed findings later:
- `read_file("scratch/research/{topic-slug}.md")`
- Or search within the scratch file for specific data points
