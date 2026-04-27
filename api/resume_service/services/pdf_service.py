"""PDF text extraction and image processing service."""

import io
import re


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts).strip() or "(empty PDF text)"


def _strip_latex_comments(tex: str) -> str:
    # Remove LaTeX comments: % not preceded by \ (escaped percent)
    lines = []
    for line in tex.split("\n"):
        cleaned = re.sub(r"(?<!\\)%.*", "", line)
        lines.append(cleaned)
    return "\n".join(lines)


def extract_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf_text(data)
    if lower.endswith(".tex"):
        return _strip_latex_comments(data.decode("utf-8", errors="replace"))
    return data.decode("utf-8", errors="replace")
