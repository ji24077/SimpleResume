"""Integration: compile routes validate input (no successful PDF required)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app


def test_compile_rejects_non_document_tex() -> None:
    client = TestClient(app)
    r = client.post("/compile", json={"tex": "just text"})
    assert r.status_code == 400
    assert "documentclass" in r.json()["detail"].lower()


def test_compile_rejects_empty_tex() -> None:
    client = TestClient(app)
    r = client.post("/compile", json={"tex": ""})
    assert r.status_code == 400
