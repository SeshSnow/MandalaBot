"""Tools for reading from and writing to the nanobot vector store."""

from pydantic import BaseModel, Field

from nanobot.tools.decorator import tool

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class VectorStoreEntry(BaseModel):
    """Content to store in the vector knowledge base."""

    content: str = Field(
        ...,
        description="The text content to embed and store in the knowledge base",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Optional tags to categorise this entry (e.g. 'brand', 'product', 'faq')",
    )
    source: str = Field(
        default="",
        description="Optional source reference (e.g. 'user conversation', 'product page')",
    )


class VectorStoreQuery(BaseModel):
    """Query to search the vector knowledge base."""

    query: str = Field(
        ...,
        description="Natural-language search query to find relevant knowledge",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of results to return (1-10)",
    )


# ---------------------------------------------------------------------------
# Search tool (LLM decides when to call this)
# ---------------------------------------------------------------------------


@tool(
    description=(
        "Search the knowledge base for information relevant to the current "
        "conversation. Use this when the user asks about something that may "
        "have been previously stored — brand facts, product details, guidelines, "
        "prior research results, or any other saved knowledge. Returns the most "
        "relevant entries ranked by semantic and keyword similarity."
    ),
)
async def search_knowledge(params: VectorStoreQuery) -> str:
    """
    Perform hybrid semantic + keyword search against the vector store.

    Returns formatted results or a message if nothing was found.
    """
    from nanobot.services.vector_store_service import get_vector_store

    search_text = params.query.strip()
    if not search_text:
        return "No search query provided."

    try:
        store = get_vector_store()
        results = await store.search(search_text, limit=params.limit)
    except Exception as exc:
        return f"Knowledge base search failed: {exc}"

    if not results:
        return "No relevant knowledge found."

    parts = []
    for i, hit in enumerate(results, 1):
        meta = hit.get("metadata") or {}
        tags = meta.get("tags", [])
        tag_str = f"  [tags: {', '.join(tags)}]" if tags else ""
        parts.append(f"{i}. {hit['content']}{tag_str}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Write tool
# ---------------------------------------------------------------------------


@tool(
    description=(
        "Save a piece of knowledge to the vector store so it can be recalled in "
        "future conversations. Use this when the user shares important facts, "
        "preferences, brand guidelines, or any information worth remembering "
        "long-term. The content will be embedded and available for semantic search."
    ),
)
async def remember_knowledge(entry: VectorStoreEntry) -> str:
    """
    Embed and persist content in the nanobot vector store.

    Returns a confirmation message or an error description.
    """
    from nanobot.services.vector_store_service import get_vector_store

    content = entry.content.strip()
    if not content:
        return "Nothing to store — content was empty."

    metadata = {}
    if entry.tags:
        metadata["tags"] = entry.tags
    if entry.source:
        metadata["source"] = entry.source

    try:
        store = get_vector_store()
        await store.add(content, metadata)
    except Exception as exc:
        return f"Failed to save to knowledge base: {exc}"

    tag_note = f" (tags: {', '.join(entry.tags)})" if entry.tags else ""
    return f"Saved to knowledge base{tag_note}: {content[:120]}{'...' if len(content) > 120 else ''}"
