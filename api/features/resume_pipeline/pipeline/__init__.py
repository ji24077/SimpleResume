"""Deterministic gates (lint, compile, PDF, ATS) and LLM hook placeholders."""

from .ats_check import ATS_AUTOFIX_ISSUE_CODES, ats_smoke_test, should_autofix_ats
from .lint import lint_latex
from .pdf_checks import page_count_from_pdf_bytes
from .signals import HardCheckResult, Signal, run_hard_checks

__all__ = [
    "ATS_AUTOFIX_ISSUE_CODES",
    "HardCheckResult",
    "Signal",
    "run_hard_checks",
    "lint_latex",
    "ats_smoke_test",
    "should_autofix_ats",
    "page_count_from_pdf_bytes",
]
