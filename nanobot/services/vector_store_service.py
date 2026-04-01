"""
Vector store service for hybrid semantic + keyword retrieval.

Uses Qwen3-Embedding-8B (via OpenRouter) with Matryoshka truncation to 2000
dimensions (pgvector HNSW max).  Stores and searches embeddings in PostgreSQL via pgvector,
combining cosine similarity with BM25-style full-text ranking.
"""

import json
import logging
from typing import Any

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from nanobot.db.session import get_db_context

logger = logging.getLogger(__name__)

# Maximum characters per content chunk to embed (safety cap)
_MAX_CONTENT_LENGTH = 8_000


def _get_config():
    from nanobot.config.mandala import MandalaConfig
    return MandalaConfig()


class VectorStoreService:
    """
    Hybrid vector store backed by PostgreSQL + pgvector.

    Provides embedding generation, row insertion, and hybrid search
    (semantic cosine + keyword BM25) against the ``nanobot_vector_store`` table.
    """

    def __init__(self) -> None:
        """Initialise the embedding client from settings."""
        cfg = _get_config()
        api_key = cfg.openrouter_api_key
        if not api_key:
            logger.warning("OPENROUTER_API_KEY not set — vector store will be disabled")
        self._client = AsyncOpenAI(
            base_url=cfg.openrouter_base_url,
            api_key=api_key or "sk-placeholder",
        )
        self._model = cfg.vector_store_embedding_model
        self._dims = cfg.vector_store_embedding_dims

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    async def get_embedding(self, text_input: str) -> list[float]:
        """
        Fetch a Qwen3 embedding with Matryoshka truncation.

        Args:
            text_input: The text to embed.

        Returns:
            A list of floats with length ``self._dims``.

        Raises:
            RuntimeError: When the embedding API call fails.
        """
        try:
            resp = await self._client.embeddings.create(
                input=text_input,
                model=self._model,
                dimensions=self._dims,
            )
            return resp.data[0].embedding
        except Exception as exc:
            logger.error("Embedding API error: %s", exc)
            raise RuntimeError(f"Embedding API error: {exc}") from exc

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """
        Insert a content row with its embedding into the vector store.

        Args:
            content: Text to store and embed.
            metadata: Optional JSON-serialisable metadata dict.
            session: Optional existing async session; a new one is created
                     if not provided.
        """
        if not content or not content.strip():
            logger.debug("Skipping empty content for vector store add")
            return
        if len(content) > _MAX_CONTENT_LENGTH:
            logger.warning(
                "Content truncated from %d to %d chars for embedding",
                len(content),
                _MAX_CONTENT_LENGTH,
            )
            content = content[:_MAX_CONTENT_LENGTH]

        vector = await self.get_embedding(content)
        meta_json = json.dumps(metadata or {})

        sql = text(
            """
            INSERT INTO nanobot_vector_store (content, embedding, metadata, fts_tokens)
            VALUES (
                :content,
                :embedding,
                CAST(:metadata AS jsonb),
                to_tsvector('english', :content_fts)
            )
            """
        )
        params = {
            "content": content,
            "embedding": str(np.array(vector).tolist()),
            "metadata": meta_json,
            "content_fts": content,
        }

        if session is not None:
            await session.execute(sql, params)
        else:
            async with get_db_context() as sess:
                await sess.execute(sql, params)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        limit: int = 5,
        *,
        session: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining semantic cosine similarity and
        BM25-style keyword ranking.

        The final score is ``0.8 * semantic + 0.2 * keyword``.

        Args:
            query: The user's search text.
            limit: Maximum number of results.
            session: Optional existing async session.

        Returns:
            A list of dicts with keys ``content``, ``metadata``,
            ``semantic_score``, and ``keyword_score``, ordered by combined
            relevance descending.  Returns an empty list on any failure so
            the chat path is never broken.
        """
        if not query or not query.strip():
            return []

        try:
            vector = await self.get_embedding(query)
        except RuntimeError:
            logger.warning("Embedding failed for search query — returning empty results")
            return []

        sql = text(
            """
            SELECT
                content,
                metadata,
                (1 - (embedding <=> :embedding::vector)) AS semantic_score,
                ts_rank_cd(fts_tokens, plainto_tsquery('english', :query)) AS keyword_score
            FROM nanobot_vector_store
            WHERE embedding IS NOT NULL
            ORDER BY (
                (1 - (embedding <=> :embedding::vector)) * 0.8
                + ts_rank_cd(fts_tokens, plainto_tsquery('english', :query)) * 0.2
            ) DESC
            LIMIT :limit
            """
        )
        params = {
            "embedding": str(np.array(vector).tolist()),
            "query": query,
            "limit": limit,
        }

        try:
            if session is not None:
                result = await session.execute(sql, params)
            else:
                async with get_db_context() as sess:
                    result = await sess.execute(sql, params)

            rows = result.fetchall()
            return [
                {
                    "content": row.content,
                    "metadata": row.metadata,
                    "semantic_score": float(row.semantic_score),
                    "keyword_score": float(row.keyword_score),
                }
                for row in rows
            ]
        except Exception as exc:
            logger.error("Vector store search failed: %s", exc)
            return []


# ---------------------------------------------------------------------------
# Module-level lazy singleton
# ---------------------------------------------------------------------------
_vector_store: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Return the shared VectorStoreService instance (created on first use)."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store
