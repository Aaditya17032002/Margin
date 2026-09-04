"""Processing a new amendment.

An amendment is not analysed on its own. It is added to the package and the
whole package is read again, because a clause in an amendment is meaningless
without the clause it edits — and reading only the amendment is how a team ends
up compliant with the change and non-compliant with everything around it.

So this task re-runs the analysis. The impact — what changed, what it
invalidates, which deadlines moved — falls out of reconciling that read against
the Requirement Ledger, in `app.pipeline.amendments`, and is recorded on the
analysis as an amendment record.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.workers.run_analysis import run_analysis_task

logger = get_logger()


async def refresh_amendment_task(ctx: dict, analysis_id: str, document_id: str) -> dict:
    logger.info("refresh_amendment_start", analysis_id=analysis_id, document_id=document_id)
    result = await run_analysis_task(ctx, analysis_id)
    return {**result, "document_id": document_id}
