"""Thin wrapper around existing compile path (no duplicate engines)."""

from __future__ import annotations

from typing import Any

# api/ is the app cwd when running uvicorn
from compile_pdf import compile_latex_to_pdf


def compile_latex(tex_source: str) -> tuple[bytes | None, dict[str, Any] | None]:
    """
    Compile LaTeX source to PDF bytes.

    Delegates to ``compile_pdf.compile_latex_to_pdf`` (sanitize + temp dir + pdflatex/latexmk/tectonic).
    """
    return compile_latex_to_pdf(tex_source)
