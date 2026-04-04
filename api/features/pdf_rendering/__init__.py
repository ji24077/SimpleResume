"""PDF rendering: compile LaTeX to PDF (Docker / latexmk)."""

from .compile_pdf import (
    compile_latex_to_pdf,
    compiler_available,
    count_pdf_pages_from_bytes,
    normalize_to_dhruv_template,
    pdf_bottom_strip_mean_luminance,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)

__all__ = [
    "compile_latex_to_pdf",
    "compiler_available",
    "count_pdf_pages_from_bytes",
    "normalize_to_dhruv_template",
    "pdf_bottom_strip_mean_luminance",
    "sanitize_latex_for_overleaf",
    "sanitize_unicode_for_latex",
]
