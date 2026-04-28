"""Unit tests: structured resume parsing and deterministic LaTeX fragments."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from features.generation.structured_resume import (
    PublicationEntry,
    parse_resume_data,
    render_publications,
    tex_plain,
)


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


# --- Publications -------------------------------------------------------------


def test_publications_default_empty_list() -> None:
    raw = {
        "header": {"name": "X"},
        "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
    }
    data = parse_resume_data(raw)
    assert data.publications == []


def test_publication_entry_requires_title() -> None:
    with pytest.raises(ValidationError):
        PublicationEntry(title="")


def test_render_publications_empty_returns_empty_string() -> None:
    assert render_publications([]) == ""


def test_render_publications_full_entry_matches_jake_gutierrez_shape() -> None:
    pub = PublicationEntry(
        title="CyCLeGen: Cycle-Consistent Layout Prediction and Image Generation",
        authors=["X. Shan", "H. Shen", "A. Anand", "Z. Tu"],
        self_name="A. Anand",
        venue="European Conference on Computer Vision",
        venue_short="ECCV 2026",
        year="2026",
        type="conference",
        status="Under review at",
        link="arXiv:2603.14957",
    )
    out = render_publications([pub])
    # Section + list scaffold
    assert "\\section{Publications}" in out
    assert "\\resumeSubHeadingListStart" in out
    assert "\\resumeSubHeadingListEnd" in out
    # Title bolded
    assert "\\textbf{CyCLeGen: Cycle-Consistent Layout Prediction and Image Generation}" in out
    # Self bolded; co-authors plain
    assert "\\textbf{A. Anand}" in out
    assert "X. Shan" in out and "H. Shen" in out and "Z. Tu" in out
    # Status + italic venue + bold short inside italic
    assert "Under review at \\textit{European Conference on Computer Vision \\textbf{ECCV 2026}}" in out
    # Link present at end
    assert "arXiv:2603.14957" in out


def test_render_publications_self_match_is_case_insensitive() -> None:
    pub = PublicationEntry(
        title="Some Paper",
        authors=["Jane Doe", "JOHN SMITH"],
        self_name="john smith",
    )
    out = render_publications([pub])
    assert "\\textbf{JOHN SMITH}" in out
    assert "\\textbf{Jane Doe}" not in out


def test_render_publications_collapses_when_optional_fields_empty() -> None:
    pub = PublicationEntry(title="Solo Paper")
    out = render_publications([pub])
    # Only the title segment should appear; no \newline second line
    assert "\\textbf{Solo Paper}" in out
    assert "\\newline" not in out
    assert "\\textit{" not in out


def test_render_publications_year_used_when_short_missing() -> None:
    pub = PublicationEntry(
        title="P",
        venue="Some Venue",
        year="2024",
    )
    out = render_publications([pub])
    assert "\\textit{Some Venue \\textbf{2024}}" in out


def test_render_publications_link_only_no_venue() -> None:
    pub = PublicationEntry(title="P", link="https://example.com/paper")
    out = render_publications([pub])
    assert "\\newline" in out
    assert "https://example.com/paper" in out


def test_render_publications_escapes_latex_specials_in_title_and_authors() -> None:
    pub = PublicationEntry(
        title="A & B: 100% Coverage",
        authors=["R&D Person"],
        self_name="R&D Person",
    )
    out = render_publications([pub])
    # Ampersand escaped
    assert "\\&" in out
    # Percent escaped
    assert "100\\%" in out
    # Self still bolded after escape
    assert "\\textbf{R\\& D Person}" in out or "\\textbf{R\\&D Person}" in out
