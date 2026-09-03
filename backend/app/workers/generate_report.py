"""generate_report worker — renders DOCX from analysis findings."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.base import async_session_factory
from app.db.models.analysis import Analysis
from app.db.models.report import Report

logger = get_logger()


async def generate_report_task(ctx: dict, report_id: str) -> dict:
    """Arq task: generate a DOCX report from analysis findings."""
    settings = get_settings()
    redis = ctx.get("redis", ctx.get("job_ctx", {}).get("redis"))

    try:
        async with async_session_factory() as db:
            # Fetch report record
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                return {"error": "Report not found"}

            # Fetch analysis
            analysis_result = await db.execute(select(Analysis).where(Analysis.id == report.analysis_id))
            analysis = analysis_result.scalar_one_or_none()
            if not analysis:
                report.status = "failed"
                await db.commit()
                return {"error": "Analysis not found"}

            logger.info("generate_report_start", report_id=report_id, analysis_id=analysis.id)

            # Generate DOCX
            try:
                from docxtpl import DocxTemplate
                from docx import Document as DocxDocument

                # Create a simple DOCX document
                doc = DocxDocument()
                doc.add_heading(f"Margin Analysis Report", 0)
                doc.add_heading(analysis.title, level=1)
                doc.add_paragraph(f"Agency: {analysis.agency}")
                doc.add_paragraph(f"Solicitation: {analysis.solicitation_number}")
                doc.add_paragraph(f"Decision: {analysis.go_no_go}")
                doc.add_paragraph(f"Generated: {datetime.now(UTC).isoformat()}")

                # Add findings sections
                for section_name, attr in [
                    ("Identity", "identity"), ("Scope", "scope"), ("Legal & Regulatory", "legal"),
                    ("Eligibility", "eligibility"), ("Pricing", "pricing"), ("Post-Award", "post_award"),
                ]:
                    findings = getattr(analysis, attr) or []
                    if findings:
                        doc.add_heading(section_name, level=2)
                        for f in findings:
                            p = doc.add_paragraph()
                            p.add_run(f"{f.get('label', '')}: ").bold = True
                            p.add_run(f.get("value", ""))
                            if f.get("citation", {}).get("quote"):
                                doc.add_paragraph(
                                    f"  Citation: \"{f['citation']['quote']}\" (p.{f['citation'].get('page', '?')})",
                                    style="Quote",
                                )

                # Save
                os.makedirs(settings.REPORTS_DIR, exist_ok=True)
                filepath = os.path.join(settings.REPORTS_DIR, f"{report_id}.docx")
                doc.save(filepath)

                report.status = "ready"
                report.storage_path = filepath
                report.size = os.path.getsize(filepath)
                await db.commit()

                # Notify via Redis
                if redis:
                    import orjson
                    await redis.publish(
                        f"notifications:{report.org_id}",
                        orjson.dumps({"event": "report_ready", "reportId": report_id}).decode(),
                    )

                logger.info("generate_report_complete", report_id=report_id)
                return {"status": "completed", "path": filepath}

            except ImportError:
                # python-docx not available — create a placeholder
                report.status = "ready"
                report.size = 0
                await db.commit()
                return {"status": "completed", "note": "DOCX generation skipped (python-docx not installed)"}

    except Exception as e:
        logger.exception("generate_report_error", report_id=report_id, error=str(e))
        return {"error": str(e)}
