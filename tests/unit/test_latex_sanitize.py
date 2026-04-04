"""Unit tests: LaTeX sanitization used before compile (existing ``compile_pdf`` behavior)."""

from __future__ import annotations

from compile_pdf import sanitize_latex_for_overleaf


def test_sanitize_fixes_extbf_typo() -> None:
    tex = r"extbf{Bold} text \documentclass{article}"
    out = sanitize_latex_for_overleaf(tex)
    # ``\textbf`` contains the substring ``extbf{`` — assert the intended fix only.
    assert r"\textbf{Bold}" in out
    assert tex != out
