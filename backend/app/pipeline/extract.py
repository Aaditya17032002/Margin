"""Plain-text extraction for uploaded documents.

Layout analysis proper belongs to the Document Intelligence provider. This is
the cheaper step in front of it: get readable text out of the bytes a person
uploaded, so a run has real material even in mock mode with no Azure keys.
"""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger()

TEXT_SUFFIXES = (".txt", ".md", ".markdown", ".csv", ".json", ".xml", ".html", ".htm", ".rtf")


def extract_text(content: bytes, filename: str) -> str:
    """Best-effort text for a document. Never raises — an unreadable upload
    still produces an analysis, it just has less to say."""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        text = _from_pdf(content)
        if text:
            return text
    elif lower.endswith(".docx"):
        text = _from_docx(content)
        if text:
            return text

    if lower.endswith(TEXT_SUFFIXES) or not lower.rpartition(".")[2]:
        return content.decode("utf-8", errors="replace")

    # Unknown binary: decoding is still better than nothing, and the reader
    # downstream drops lines that are not printable.
    decoded = content.decode("utf-8", errors="ignore")
    return decoded if decoded.strip() else ""


def _from_pdf(content: bytes) -> str:
    try:
        import io

        from pypdf import PdfReader
    except ImportError:
        logger.warning("pdf_extract_unavailable", reason="pypdf not installed")
        return ""

    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(p for p in pages if p)
    except Exception as exc:  # noqa: BLE001 — a bad PDF must not fail the upload
        logger.warning("pdf_extract_failed", error=str(exc))
        return ""


def _from_docx(content: bytes) -> str:
    try:
        import io

        from docx import Document as DocxDocument
    except ImportError:
        return ""

    try:
        doc = DocxDocument(io.BytesIO(content))
        parts = [p.text.strip() for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        return "\n".join(p for p in parts if p)
    except Exception as exc:  # noqa: BLE001
        logger.warning("docx_extract_failed", error=str(exc))
        return ""
