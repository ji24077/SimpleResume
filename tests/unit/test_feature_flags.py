"""Feature flags: Pydantic defaults are False (env may override at runtime; CI checks contract)."""

from __future__ import annotations


def test_feature_flag_field_defaults_false() -> None:
    from main import Settings

    assert Settings.model_fields["feature_pdf_annotations"].default is False
    assert Settings.model_fields["feature_advanced_diagnostics"].default is False
