"""Document ingest → layout → chunk → embed → index pipeline."""

from __future__ import annotations

from app.core.logging import get_logger
from app.providers.base import ChunkResult, LayoutResult
from app.pipeline.extract import pages_from_text
from app.pipeline.layout import LayoutExtractor
from app.providers.factory import get_docintel_provider, get_llm_provider

logger = get_logger()


async def ingest_document(content: bytes, filename: str) -> LayoutResult:
    """Step 1: Extract layout from uploaded document."""
    provider = get_docintel_provider()
    logger.info("pipeline_ingest", filename=filename, size=len(content))
    return await provider.extract_layout(content, filename)


async def embed_chunks(chunks: list[ChunkResult]) -> list[list[float]]:
    """Step 2: Generate embeddings for all chunks."""
    provider = get_llm_provider()
    texts = [c.text for c in chunks]
    if not texts:
        return []
    logger.info("pipeline_embed", chunk_count=len(texts))
    return await provider.embed(texts)


async def full_pipeline(content: bytes, filename: str) -> tuple[LayoutResult, list[list[float]]]:
    """Run the complete ingest → layout → chunk → embed pipeline."""
    layout = await ingest_document(content, filename)
    embeddings = await embed_chunks(layout.chunks)
    return layout, embeddings


async def full_pipeline_from_text(
    raw_text: str, filename: str
) -> tuple[LayoutResult, list[list[float]]]:
    """The same pipeline for text that was extracted at upload time.

    Re-encoding stored text and handing it back to the PDF parser under its
    original filename only produced a confusing "invalid pdf header" warning on
    every run — the bytes stopped being a PDF the moment they were extracted.
    """
    layout = LayoutExtractor().extract_from_pages(pages_from_text(raw_text), filename, raw_text=raw_text)
    embeddings = await embed_chunks(layout.chunks)
    return layout, embeddings
