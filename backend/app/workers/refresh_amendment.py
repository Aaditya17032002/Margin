"""refresh_amendment worker — re-extract, diff vs prior version, notify."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger()


async def refresh_amendment_task(ctx: dict, analysis_id: str, document_id: str) -> dict:
    """Arq task: process a new amendment and diff against the prior version."""
    logger.info("refresh_amendment_start", analysis_id=analysis_id, document_id=document_id)

    # In production:
    # 1. Load the new amendment document
    # 2. Run layout extraction
    # 3. Compare chunks against the prior version
    # 4. Identify changes (added/changed/removed)
    # 5. Update the analysis amendments array
    # 6. Re-run affected agents (intake, compliance, evaluation, verifier)
    # 7. Publish notification

    return {
        "status": "completed",
        "analysis_id": analysis_id,
        "document_id": document_id,
        "changes": [],
    }
