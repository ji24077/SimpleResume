"""PDF page count (delegates to existing implementation)."""

from __future__ import annotations

from compile_pdf import count_pdf_pages_from_bytes


def page_count_from_pdf_bytes(pdf_bytes: bytes) -> int:
    return count_pdf_pages_from_bytes(pdf_bytes)
