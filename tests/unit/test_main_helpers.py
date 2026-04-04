"""Unit tests: helpers in ``main`` (JSON repair, preview/coaching parse, extract_text)."""

from __future__ import annotations

from main import _parse_preview_coaching, extract_text, repair_json


def test_repair_json_strips_markdown_fence() -> None:
    raw = """```json
{"a": 1, "b": "two"}
```"""
    assert repair_json(raw) == {"a": 1, "b": "two"}


def test_parse_preview_coaching_aligns_bullets_and_coaching() -> None:
    data = {
        "preview_sections": [
            {
                "kind": "experience",
                "title": "Job",
                "bullets": ["b1", "b2"],
            }
        ],
        "coaching": [{"section_why": "why", "items": [{"why_better": "x"}]}],
    }
    prev, coach = _parse_preview_coaching(data)
    assert len(prev) == 1
    assert len(prev[0].bullets) == 2
    assert len(coach) == 1
    assert len(coach[0].items) == 2
    assert coach[0].items[0].why_better == "x"
    assert coach[0].items[1].why_better == ""


def test_extract_text_tex_utf8() -> None:
    assert extract_text("cv.tex", b"\\documentclass{article}\nHi").startswith("\\documentclass")
