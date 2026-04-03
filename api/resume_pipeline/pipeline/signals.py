"""Decision layer: lint → compile → pages → ATS (all deterministic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ats_check import ats_smoke_test
from .compile import compile_latex
from .lint import lint_latex
from .pdf_checks import page_count_from_pdf_bytes


@dataclass(frozen=True)
class Signal:
    """Reason to invoke a fixer (LLM or other); produced only by machine checks here."""

    kind: str
    detail: Any


@dataclass
class HardCheckResult:
    """Outcome of a full deterministic pass."""

    ok: bool
    signal: Signal | None
    pdf_bytes: bytes | None
    page_count: int | None
    lint_errors: list[str]


def run_hard_checks(
    latex: str,
    *,
    allow_multi_page: bool = False,
    skip_ats: bool = False,
) -> HardCheckResult:
    """
    Run lint, compile, optional one-page policy, optional ATS smoke test.

    Does not call any LLM. Uses the same compile stack as the live API.
    """
    lint_errors = lint_latex(latex)
    if lint_errors:
        return HardCheckResult(
            ok=False,
            signal=Signal("fix_lint", lint_errors),
            pdf_bytes=None,
            page_count=None,
            lint_errors=lint_errors,
        )

    pdf, err = compile_latex(latex)
    if not pdf:
        return HardCheckResult(
            ok=False,
            signal=Signal("fix_compile_error", err),
            pdf_bytes=None,
            page_count=None,
            lint_errors=[],
        )

    try:
        pages = page_count_from_pdf_bytes(pdf)
    except (ValueError, OSError) as e:
        return HardCheckResult(
            ok=False,
            signal=Signal("page_count_failed", str(e)),
            pdf_bytes=pdf,
            page_count=None,
            lint_errors=[],
        )

    if pages > 1 and not allow_multi_page:
        return HardCheckResult(
            ok=False,
            signal=Signal("fit_one_page", pages),
            pdf_bytes=pdf,
            page_count=pages,
            lint_errors=[],
        )

    if not skip_ats:
        ats_issue = ats_smoke_test(pdf)
        if ats_issue:
            return HardCheckResult(
                ok=False,
                signal=Signal("fix_ats", ats_issue),
                pdf_bytes=pdf,
                page_count=pages,
                lint_errors=[],
            )

    return HardCheckResult(
        ok=True,
        signal=None,
        pdf_bytes=pdf,
        page_count=pages,
        lint_errors=[],
    )
