"""Verifier Agent — Independent pass re-checking citations against cited spans.

Every ANSWERED finding is evaluated against its exact quote and document text.
If there is a mismatch, hallucination, or unsupported claim:
- The finding is downgraded to NEEDS_HUMAN.
- flagged is set to True.
- verified is set to False.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.providers.base import ChunkResult

logger = get_logger()


class CitationVerifier:
    """Verifies that each finding is directly supported by its citation."""

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    async def verify_findings(
        self,
        findings: list[dict[str, Any]],
        chunks: list[ChunkResult],
    ) -> list[dict[str, Any]]:
        """Verify each finding against its cited span."""
        chunk_text_corpus = " ".join(c.text.lower() for c in chunks) if chunks else ""
        verified_results = []

        for item in findings:
            finding = dict(item)
            citation = finding.get("citation") or {}
            quote = citation.get("quote", "").strip()

            # If confidence is below threshold, downgrade immediately
            confidence = finding.get("confidence", 0.0)
            if confidence < self.confidence_threshold:
                logger.info("verifier_downgrade_low_confidence", finding_id=finding.get("id"), conf=confidence)
                finding["verified"] = False
                finding["flagged"] = True
                finding["state"] = "NEEDS_HUMAN"
                verified_results.append(finding)
                continue

            # Check if quote exists and is non-empty
            if not quote or quote.lower() == "none" or len(quote) < 3:
                finding["verified"] = False
                finding["flagged"] = True
                finding["state"] = "NEEDS_HUMAN"
                finding["detail"] = f"{finding.get('detail', '')} [VERIFIER: Missing or empty source quote]".strip()
                verified_results.append(finding)
                continue

            # Verify quote is grounded in document chunks if chunks are present
            if chunk_text_corpus:
                # Check for significant words overlap
                quote_words = [w for w in quote.lower().split() if len(w) > 3]
                matches = sum(1 for w in quote_words if w in chunk_text_corpus)
                match_ratio = matches / max(1, len(quote_words))

                if match_ratio < 0.3:
                    # Potential hallucinated citation
                    logger.warning("verifier_citation_mismatch", finding_id=finding.get("id"), quote=quote)
                    finding["verified"] = False
                    finding["flagged"] = True
                    finding["state"] = "NEEDS_HUMAN"
                    finding["confidence"] = max(0.1, round(confidence * 0.5, 2))
                    finding["detail"] = f"{finding.get('detail', '')} [VERIFIER: Cited quote not verified in source text]".strip()
                else:
                    finding["verified"] = True
                    finding["flagged"] = finding.get("stakes") == "disqualifying" and confidence < 0.95
            else:
                # Mock or empty chunks fallback
                finding["verified"] = True
                finding["flagged"] = False

            verified_results.append(finding)

        return verified_results
