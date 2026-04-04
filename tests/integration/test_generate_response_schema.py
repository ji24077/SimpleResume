"""Integration: public response model stays backward compatible (optional fields)."""

from __future__ import annotations

from main import GenerateResponse


def test_generate_response_accepts_legacy_required_fields_only() -> None:
    m = GenerateResponse(
        latex_document="",
        preview_sections=[],
        coaching=[],
    )
    assert m.pdf_page_count is None
    assert m.quality_issues is None
    assert m.ats_issue_code is None
    assert m.one_page_enforced is False
