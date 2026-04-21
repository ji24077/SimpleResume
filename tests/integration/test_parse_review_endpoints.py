"""Integration: /resume/parse and /resume/generate-from-structured honor the feature flag."""

from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

import main as main_module


def _client() -> TestClient:
    return TestClient(main_module.app)


def test_parse_returns_404_when_feature_flag_off() -> None:
    with mock.patch.object(main_module.settings, "feature_parse_review", False):
        r = _client().post("/resume/parse", data={"text": "some resume"})
    assert r.status_code == 404


def test_generate_from_structured_returns_404_when_feature_flag_off() -> None:
    body = {
        "resume_data": {
            "header": {"name": "Ada"},
            "skills": {"languages": ["Python"], "frameworks": [], "tools": []},
        },
        "page_policy": "strict_one_page",
    }
    with mock.patch.object(main_module.settings, "feature_parse_review", False):
        r = _client().post("/resume/generate-from-structured", json=body)
    assert r.status_code == 404


def test_parse_returns_503_when_no_api_key_but_flag_on() -> None:
    with mock.patch.object(main_module.settings, "feature_parse_review", True), mock.patch.object(
        main_module.settings, "openai_api_key", ""
    ):
        r = _client().post("/resume/parse", data={"text": "resume body"})
    assert r.status_code == 503


def test_parse_requires_file_or_text() -> None:
    with mock.patch.object(main_module.settings, "feature_parse_review", True), mock.patch.object(
        main_module.settings, "openai_api_key", "sk-test-placeholder"
    ):
        r = _client().post("/resume/parse", data={})
    assert r.status_code == 400


def test_generate_from_structured_validates_resume_data_shape() -> None:
    bad_body = {
        "resume_data": {"header": {}, "skills": {"languages": [], "frameworks": [], "tools": []}},
        "page_policy": "strict_one_page",
    }
    with mock.patch.object(main_module.settings, "feature_parse_review", True), mock.patch.object(
        main_module.settings, "openai_api_key", "sk-test-placeholder"
    ):
        r = _client().post("/resume/generate-from-structured", json=bad_body)
    assert r.status_code == 422
    detail = r.json().get("detail", {})
    assert detail.get("error") == "resume_data_invalid"


def test_generate_from_structured_rejects_non_object_resume_data() -> None:
    with mock.patch.object(main_module.settings, "feature_parse_review", True), mock.patch.object(
        main_module.settings, "openai_api_key", "sk-test-placeholder"
    ):
        r = _client().post(
            "/resume/generate-from-structured",
            json={"resume_data": "not an object", "page_policy": "strict_one_page"},
        )
    # Pydantic 422 for body parse before reaching validator.
    assert r.status_code in (422, 400)
