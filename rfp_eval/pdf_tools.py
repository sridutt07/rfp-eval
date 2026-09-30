"""Document Tool: extracts clean text from supplier RFP PDFs."""

from __future__ import annotations

from pathlib import Path


class PDFReadError(Exception):
    """Raised when a PDF cannot be read or contains no extractable text."""


def extract_text(pdf_path: str | Path, max_chars: int = 60_000) -> str:
    """Extract text from every page of a PDF, normalized to clean plain text.

    Raises:
        PDFReadError: if the file cannot be opened or yields no text.
    """
    try:
        import pymupdf
    except ImportError:  # older PyMuPDF versions
        import fitz as pymupdf

    path = Path(pdf_path)
    if not path.exists():
        raise PDFReadError(f"File not found: {path}")
    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:  # noqa: BLE001 - surface as domain error
        raise PDFReadError(f"Could not open PDF '{path.name}': {exc}") from exc

    pages: list[str] = []
    try:
        for page in doc:
            pages.append(page.get_text("text"))
    finally:
        doc.close()

    text = "\n".join(pages)
    # Normalize whitespace: collapse runs of blank lines, strip trailing spaces.
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned = "\n".join(lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    cleaned = cleaned.strip()

    if not cleaned:
        raise PDFReadError(f"No extractable text found in '{path.name}' (scanned image?).")
    return cleaned[:max_chars]
