"""
Research scratch pad tool.

Fetches multiple web sources, saves raw content to scratch files,
returns only a concise summary. Keeps conversation context lean.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60].strip("-")


class ResearchScratchTool(Tool):
    """
    Deep research with scratch pad.

    Fetches web pages, saves raw content to scratch files,
    returns only a summary to keep conversation context lean.
    """

    def __init__(self, workspace: Path, web_fetch_fn=None, web_search_fn=None):
        self.workspace = workspace
        self._web_fetch = web_fetch_fn
        self._web_search = web_search_fn

    @property
    def name(self) -> str:
        return "research"

    @property
    def description(self) -> str:
        return (
            "Deep web research with scratch pad. Searches the web, fetches multiple sources, "
            "saves all findings to a scratch file, and returns only a concise summary. "
            "Use this instead of calling web_search + web_fetch multiple times. "
            "Keeps conversation context lean by storing raw content in scratch files."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "What to research",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: specific URLs to fetch in addition to search results",
                },
                "depth": {
                    "type": "string",
                    "enum": ["quick", "standard", "deep"],
                    "description": "Research depth: quick (3 sources), standard (5), deep (10). Default: standard",
                },
            },
            "required": ["topic"],
        }

    async def execute(
        self,
        topic: str,
        sources: list[str] | None = None,
        depth: str = "standard",
        **kwargs: Any,
    ) -> str:
        # Determine source count
        source_limits = {"quick": 3, "standard": 5, "deep": 10}
        max_sources = source_limits.get(depth, 5)

        # Search the web
        search_results = []
        if self._web_search:
            try:
                search_response = await self._web_search(query=topic, count=max_sources)
                if isinstance(search_response, str):
                    search_results = [{"url": "", "title": "", "snippet": search_response}]
                elif isinstance(search_response, dict):
                    search_results = search_response.get("results", [])
                elif isinstance(search_response, list):
                    search_results = search_response
            except Exception:
                pass

        # Add explicit sources
        if sources:
            for url in sources:
                search_results.append({"url": url, "title": url, "snippet": ""})

        if not search_results:
            return f"No sources found for: {topic}"

        # Fetch each source and extract content
        findings = []
        fetched_count = 0

        for result in search_results[:max_sources]:
            url = result.get("url", "")
            title = result.get("title", url)
            snippet = result.get("snippet", "")

            content = snippet  # Fallback to snippet

            if url and self._web_fetch:
                try:
                    fetch_result = await self._web_fetch(url=url)
                    if isinstance(fetch_result, str):
                        content = fetch_result[:5000]  # Cap at 5K per source
                    elif isinstance(fetch_result, dict):
                        content = fetch_result.get("content", snippet)[:5000]
                except Exception:
                    content = snippet

            findings.append({
                "title": title,
                "url": url,
                "content": content,
            })
            fetched_count += 1

        # Write scratch file
        slug = _slugify(topic)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        scratch_dir = self.workspace / "scratch" / "research"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        scratch_file = scratch_dir / f"{slug}.md"

        lines = [
            f"# Research: {topic}",
            f"Date: {now}",
            f"Sources: {fetched_count}",
            f"Depth: {depth}",
            "",
        ]

        for i, f in enumerate(findings, 1):
            lines.append(f"## Source {i}: {f['title']}")
            if f["url"]:
                lines.append(f"URL: {f['url']}")
            lines.append("")
            lines.append(f["content"][:3000])  # Cap content per source in scratch
            lines.append("")
            lines.append("---")
            lines.append("")

        scratch_file.write_text("\n".join(lines), encoding="utf-8")

        # Return ONLY the summary — not the raw content
        summary_lines = [
            f"Research complete: {topic}",
            f"Sources consulted: {fetched_count}",
            f"Scratch file: scratch/research/{slug}.md",
            "",
            "Key findings:",
        ]

        for f in findings[:5]:
            snippet = f["content"][:200].replace("\n", " ").strip()
            if snippet:
                summary_lines.append(f"- {f['title']}: {snippet}...")

        return "\n".join(summary_lines)
