"""Unit tests: LaTeX/Unicode sanitizers (no Docker)."""

from __future__ import annotations

from compile_pdf import sanitize_unicode_for_latex


def test_sanitize_unicode_strips_problematic_chars() -> None:
    out = sanitize_unicode_for_latex("hello\u200bworld")
    assert "\u200b" not in out
    assert "hello" in out and "world" in out
