"""Deterministic LaTeX pre-checks (no LLM)."""

from __future__ import annotations

import re


def _has_unmatched_braces(tex: str) -> bool:
    """Rough balance of `{` / `}` skipping `\\` escapes (not full TeX parser)."""
    depth = 0
    i = 0
    n = len(tex)
    while i < n:
        c = tex[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return True
        i += 1
    return depth != 0


def _has_non_ascii(tex: str) -> bool:
    """Flag non-ASCII in source (resume policy is ASCII-first for body text)."""
    return any(ord(ch) > 127 for ch in tex)


def lint_latex(tex: str) -> list[str]:
    """
    Return a list of issue codes (empty if no problems detected).

    Intended as a first filter before ``compile_latex_to_pdf``; does not replace compile.
    """
    errors: list[str] = []
    if not tex or not tex.strip():
        errors.append("empty_tex")
        return errors

    # Two backslashes before % in the .tex source (line-break + bad percent escape pattern).
    if "\\\\%" in tex:
        errors.append("double_backslash_percent")

    if re.search(r"\\href\s*\{\s*\}", tex):
        errors.append("empty_href")

    if _has_unmatched_braces(tex):
        errors.append("brace_mismatch")

    if _has_non_ascii(tex):
        errors.append("unicode_detected")

    if "\\documentclass" not in tex:
        errors.append("missing_documentclass")

    return errors
