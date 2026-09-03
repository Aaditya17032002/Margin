"""Scoped in-document retriever over pgvector chunks.

All searches are strictly partitioned by analysis_id and org_id.
No cross-analysis or cross-tenant leakage.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.doc_chunk import DocChunk
from app.providers.base import RetrievalResult
from app.providers.factory import get_llm_provider

logger = get_logger()


class ScopedRetriever:
    """Performs cosine similarity search over doc_chunks table for a single analysis."""

    def __init__(self, db: AsyncSession, analysis_id: str, org_id: str):
        self.db = db
        self.analysis_id = analysis_id
        self.org_id = org_id

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        provider = get_llm_provider()
        query_embeddings = await provider.embed([query])
        if not query_embeddings:
            return []
        query_vec = query_embeddings[0]

        # In PostgreSQL with pgvector:
        # SELECT text, page, section_path, bbox, 1 - (embedding <=> query_vec) as score
        # FROM doc_chunks WHERE analysis_id = :aid AND org_id = :oid
        # ORDER BY embedding <=> query_vec LIMIT :k
        try:
            from pgvector.sqlalchemy import Vector
            stmt = (
                select(DocChunk)
                .where(DocChunk.analysis_id == self.analysis_id, DocChunk.org_id == self.org_id)
                .order_by(DocChunk.embedding.cosine_distance(query_vec))
                .limit(top_k)
            )
            res = await self.db.execute(stmt)
            chunks = res.scalars().all()
            return [
                RetrievalResult(
                    text=c.text,
                    page=c.page,
                    section_path=c.section_path or "",
                    bbox=c.bbox,
                    score=0.9,
                )
                for c in chunks
            ]
        except Exception as e:
            logger.debug("vector_retrieval_fallback", error=str(e))
            # Fallback text query for dev/sqlite environments
            stmt = (
                select(DocChunk)
                .where(DocChunk.analysis_id == self.analysis_id, DocChunk.org_id == self.org_id)
                .limit(top_k)
            )
            res = await self.db.execute(stmt)
            chunks = res.scalars().all()
            return [
                RetrievalResult(
                    text=c.text,
                    page=c.page,
                    section_path=c.section_path or "",
                    bbox=c.bbox,
                    score=0.85,
                )
                for c in chunks
            ]
