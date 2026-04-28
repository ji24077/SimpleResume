"""Unit tests: resume_data_to_source_text preserves every fact."""

from __future__ import annotations

import pytest

from features.generation.structured_resume import (
    ResumeData,
    parse_resume_data,
    resume_data_to_source_text,
)


FULL_FIXTURE: dict = {
    "header": {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+1 555 555 0123",
        "links": [
            {"label": "GitHub", "url": "https://github.com/ada"},
            {"label": "LinkedIn", "url": "https://linkedin.com/in/ada"},
        ],
    },
    "education": [
        {
            "school": "University of London",
            "degree": "B.S. Mathematics",
            "date": "1833-1835",
            "location": "London, UK",
            "bullets": ["Graduated with honors", "Thesis on analytical engines"],
        }
    ],
    "experience": [
        {
            "title": "Analyst",
            "company": "Analytical Engine Co.",
            "date": "1842-1843",
            "location": "London",
            "bullets": [
                "Authored first algorithm for Bernoulli numbers",
                "Collaborated with Charles Babbage on engine design",
                "Documented computational notation in 7 notes",
            ],
        },
        {
            "title": "Consultant",
            "company": "Royal Society",
            "date": "1840",
            "location": "",
            "bullets": ["Advised on computation theory"],
        },
    ],
    "projects": [
        {
            "name": "Note G",
            "date": "1843",
            "tech_line": "Analytical Engine, Punched Cards",
            "bullets": [
                "Designed iterative algorithm",
                "Introduced loops and subroutines",
            ],
        }
    ],
    "skills": {
        "languages": ["English", "French"],
        "frameworks": ["Differential Calculus"],
        "tools": ["Analytical Engine", "Jacquard Loom"],
    },
}


def _build() -> ResumeData:
    return parse_resume_data(FULL_FIXTURE)


def test_serializer_header_fields_present() -> None:
    text = resume_data_to_source_text(_build())
    assert "NAME: Ada Lovelace" in text
    assert "EMAIL: ada@example.com" in text
    assert "PHONE: +1 555 555 0123" in text
    assert "- GitHub: https://github.com/ada" in text
    assert "- LinkedIn: https://linkedin.com/in/ada" in text


def test_serializer_preserves_all_experience_bullets() -> None:
    text = resume_data_to_source_text(_build())
    for bullet in FULL_FIXTURE["experience"][0]["bullets"]:
        assert bullet in text, f"missing bullet: {bullet}"
    assert "Company: Analytical Engine Co." in text
    assert "Title: Analyst" in text
    assert "Date: 1842-1843" in text


def test_serializer_preserves_all_entries() -> None:
    text = resume_data_to_source_text(_build())
    assert "=== EDUCATION ===" in text
    assert "=== EXPERIENCE ===" in text
    assert "=== PROJECTS ===" in text
    assert "=== SKILLS ===" in text
    assert "Royal Society" in text
    assert "Note G" in text


def test_serializer_preserves_project_tech_line_and_bullets() -> None:
    text = resume_data_to_source_text(_build())
    assert "Tech: Analytical Engine, Punched Cards" in text
    assert "Designed iterative algorithm" in text
    assert "Introduced loops and subroutines" in text


def test_serializer_emits_skills_as_comma_separated_lines() -> None:
    text = resume_data_to_source_text(_build())
    assert "Languages: English, French" in text
    assert "Frameworks: Differential Calculus" in text
    assert "Tools: Analytical Engine, Jacquard Loom" in text


def test_serializer_skips_empty_optional_fields() -> None:
    text = resume_data_to_source_text(_build())
    # Royal Society entry has no location; should not emit "Location: " line for it.
    rs_block = text.split("Company: Royal Society", 1)[1].split("Company:", 1)[0]
    assert "Location:" not in rs_block


def test_serializer_minimal_skips_empty_sections() -> None:
    minimal = {
        "header": {"name": "X"},
        "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
    }
    data = parse_resume_data(minimal)
    text = resume_data_to_source_text(data)
    assert "NAME: X" in text
    assert "=== EDUCATION ===" not in text
    assert "=== EXPERIENCE ===" not in text
    assert "=== PROJECTS ===" not in text
    assert "Languages: Python" in text
    assert "Frameworks:" not in text
    assert "Tools:" not in text


def test_serializer_bullet_count_matches_source() -> None:
    text = resume_data_to_source_text(_build())
    # 3 bullets in first job + 1 bullet in second job + 2 project bullets + 2 edu bullets
    bullet_lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    link_lines = 2  # GitHub, LinkedIn
    total_content_bullets = 3 + 1 + 2 + 2
    assert len(bullet_lines) == link_lines + total_content_bullets


def test_serializer_strips_interior_whitespace_on_name() -> None:
    data = parse_resume_data(
        {
            "header": {"name": "  Jane  "},
            "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
        }
    )
    text = resume_data_to_source_text(data)
    assert "NAME: Jane" in text


def test_serializer_output_ends_with_single_newline() -> None:
    text = resume_data_to_source_text(_build())
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_serializer_emits_publications_block() -> None:
    raw = {
        "header": {"name": "X"},
        "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
        "publications": [
            {
                "title": "Paper One",
                "authors": ["A. Anand", "Z. Tu"],
                "self_name": "A. Anand",
                "venue": "ECCV",
                "venue_short": "ECCV 2026",
                "year": "2026",
                "type": "conference",
                "status": "Under review at",
                "link": "arXiv:2603.14957",
            }
        ],
    }
    data = parse_resume_data(raw)
    text = resume_data_to_source_text(data)
    assert "=== PUBLICATIONS ===" in text
    assert "Title: Paper One" in text
    assert "Authors: A. Anand, Z. Tu" in text
    assert "Self: A. Anand" in text
    assert "Venue: ECCV" in text
    assert "VenueShort: ECCV 2026" in text
    assert "Year: 2026" in text
    assert "Type: conference" in text
    assert "Status: Under review at" in text
    assert "Link: arXiv:2603.14957" in text


def test_serializer_skips_publications_when_empty() -> None:
    raw = {
        "header": {"name": "X"},
        "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
    }
    data = parse_resume_data(raw)
    text = resume_data_to_source_text(data)
    assert "=== PUBLICATIONS ===" not in text
