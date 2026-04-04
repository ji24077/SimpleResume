"""Integration: HTTP surface without calling OpenAI."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_health_ok() -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "openai_configured" in body
    assert "compiler" in body
