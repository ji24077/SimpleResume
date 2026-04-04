"""Unit tests: existing LaTeX lint gate (``lint_latex``)."""

from __future__ import annotations

from features.resume_pipeline.pipeline.lint import lint_latex


def test_lint_empty_tex() -> None:
    assert "empty_tex" in lint_latex("")


def test_lint_valid_minimal_document() -> None:
    tex = r"""\documentclass{article}
\begin{document}
Hello
\end{document}
"""
    assert lint_latex(tex) == []


def test_lint_detects_empty_href() -> None:
    tex = r"""\documentclass{article}
\begin{document}
\href{}{x}
\end{document}
"""
    assert "empty_href" in lint_latex(tex)
