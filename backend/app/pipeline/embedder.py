"""Vector embedder for document chunks."""

from __future__ import annotations

from app.core.logging import get_logger
from app.providers.base import ChunkResult
from app.providers.factory import get_llm_provider

logger = get_logger()


class VectorEmbedder:
    """Generates dense vector embeddings for document chunks using the configured LLMProvider."""

    async def embed_chunks(
        self,
        chunks: list[ChunkResult],
    ) -> list[list[float]]:
        if not chunks:
            return []

        provider = get_llm_provider()
        texts = [c.text for c in chunks]

        # Process in batches of 64
        batch_size = 64
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await provider.embed(batch)
            all_embeddings.extend(embeddings)

        logger.info("chunks_embedded", total_chunks=len(chunks), vector_dim=len(all_embeddings[0]) if all_embeddings else 0)
        return all_embeddings
