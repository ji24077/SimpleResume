"""Unit tests: PDF page counting (pypdf, existing ``compile_pdf`` helper)."""

from __future__ import annotations

from io import BytesIO

from compile_pdf import count_pdf_pages_from_bytes
from pypdf import PdfWriter


def test_count_pdf_pages_single_page() -> None:
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    buf = BytesIO()
    w.write(buf)
    assert count_pdf_pages_from_bytes(buf.getvalue()) == 1
