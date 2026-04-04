"""Integration: JSON generate validates body before calling the model."""

from __future__ import annotations

from unittest import mock

from fastapi.testclient import TestClient

import main as main_module


def test_generate_json_rejects_whitespace_only_text() -> None:
    with mock.patch.object(main_module.settings, "openai_api_key", "sk-test-placeholder"):
        client = TestClient(main_module.app)
        r = client.post("/generate-json", json={"text": "  \n\t  "})
    assert r.status_code == 400
    assert "text required" in str(r.json().get("detail", "")).lower()
