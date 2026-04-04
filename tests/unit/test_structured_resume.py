"""Unit tests: structured resume parsing and deterministic LaTeX fragments."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from features.generation.structured_resume import parse_resume_data, tex_plain


def test_parse_resume_data_minimal_valid() -> None:
    raw = {
        "header": {"name": "Ada Lovelace", "email": "ada@example.com"},
        "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
    }
    data = parse_resume_data(raw)
    assert data.header.name == "Ada Lovelace"
    assert data.skills.languages == ["Python"]


def test_parse_resume_data_rejects_empty_skills() -> None:
    raw = {
        "header": {"name": "X"},
        "skills": {"languages": [], "frameworks": [], "tools": []},
    }
    with pytest.raises(ValidationError):
        parse_resume_data(raw)


def test_tex_plain_escapes_ampersand() -> None:
    assert "\\&" in tex_plain("A & B")
