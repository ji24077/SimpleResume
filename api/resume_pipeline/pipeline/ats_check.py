"""ATS-oriented smoke checks on PDF text extraction (no LLM)."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Issues that are safe to hand to the ATS fixer LLM (heading/order). Others: log only.
ATS_AUTOFIX_ISSUE_CODES: frozenset[str] = frozenset(
    {
        "missing_education_heading",
        "missing_experience_heading",
        "section_order_experience_before_education",
    }
)


def should_autofix_ats(issue_code: str | None) -> bool:
    return bool(issue_code and issue_code in ATS_AUTOFIX_ISSUE_CODES)


def _pdf_to_text_pdftotext(pdf_bytes: bytes) -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            path = Path(f.name)
        out = subprocess.check_output(
            [exe, "-layout", str(path), "-"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return out
    except (subprocess.CalledProcessError, FileNotFoundError, TimeoutError, OSError):
        return None
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def _pdf_to_text_pypdf(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return "\n\n".join(parts)


def ats_smoke_test(pdf_bytes: bytes) -> str | None:
    """
    Heuristic reading-order / heading smoke test on extracted text.

    Returns an issue code string, or ``None`` if no issue detected.
    """
    if not pdf_bytes:
        return "empty_pdf"

    text = _pdf_to_text_pdftotext(pdf_bytes)
    if text is None:
        text = _pdf_to_text_pypdf(pdf_bytes)

    if not text or not text.strip():
        return "empty_extracted_text"

    lower = text.lower()
    # Section titles as usually emitted for this template (best-effort).
    if "education" not in lower:
        return "missing_education_heading"

    if "experience" not in lower:
        return "missing_experience_heading"

    # First occurrence order (very rough ATS signal).
    edu = lower.find("education")
    exp = lower.find("experience")
    if edu >= 0 and exp >= 0 and exp < edu:
        return "section_order_experience_before_education"

    # Suspiciously little text for a one-page resume (tunable).
    alnum = len(re.findall(r"[a-zA-Z0-9]", text))
    if alnum < 200:
        return "very_sparse_text"

    return None
