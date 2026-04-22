"""Unit tests: parser prompt is strict (no rewriting / inventing) and self-contained."""

from __future__ import annotations

from prompts import build_parse_user_message, parser_system


def test_parser_system_forbids_rewriting() -> None:
    sys = parser_system()
    low = sys.lower()
    assert "extraction" in low or "extract" in low
    assert "rewrite" in low
    assert "invent" in low
    # No LaTeX instructions leaking into the parser.
    assert "\\documentclass" not in sys
    assert "latex" not in low or "latex" in low  # allowed to mention "Do NOT output LaTeX"


def test_parser_system_requires_json_only_with_resume_data_key() -> None:
    sys = parser_system()
    assert "resume_data" in sys
    assert "json" in sys.lower()


def test_parse_user_message_includes_raw_source_and_schema() -> None:
    raw = "John Doe\njohn@example.com\nSoftware Engineer at Acme (2021-2024)"
    msg = build_parse_user_message(raw)
    assert "--- RESUME SOURCE ---" in msg
    assert "John Doe" in msg
    assert "john@example.com" in msg
    assert "Software Engineer at Acme" in msg
    # Schema reference (Pydantic JSON Schema) should mention header + skills.
    assert "header" in msg
    assert "skills" in msg


def test_parse_user_message_handles_empty_source() -> None:
    msg = build_parse_user_message("")
    assert "(empty)" in msg
    assert "resume_data" in msg
