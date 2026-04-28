"""Integration: /resume/bullet-chat NDJSON streaming behind FEATURE_BULLET_CHAT."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def client_with_chat(monkeypatch):
    """Build a fresh FastAPI app that includes the bullet-chat router.

    Patches settings attributes directly (no module reload) so the test is
    independent of whether OPENAI_API_KEY / FEATURE_BULLET_CHAT are set in
    the environment that imported the modules.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from resume_service.config import settings
    from resume_service.routers import bullet_chat as bc_router

    monkeypatch.setattr(settings, "feature_bullet_chat", True)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    app = FastAPI()
    app.include_router(bc_router.router)

    def fake_refine_bullet(**_kwargs):
        yield {"type": "progress", "message": "Refining bullet…"}
        yield {
            "type": "result",
            "data": {
                "mode": "rewrite",
                "proposed_text": "Led $2.4M monthly revenue",
                "assistant_message": "Done.",
            },
        }

    monkeypatch.setattr(
        "resume_service.routers.bullet_chat.refine_bullet", fake_refine_bullet
    )
    # Avoid creating a real OpenAI client (it's instantiated even though the
    # service-level call is monkeypatched).
    monkeypatch.setattr(
        "resume_service.routers.bullet_chat.get_openai_client", lambda: object()
    )
    return TestClient(app)


def test_bullet_chat_route_streams_ndjson(client_with_chat) -> None:
    body = {
        "issue_id": "iss_1",
        "original_text": "Increased revenue by 40% annually",
        "baseline_suggestion": "Drove $2.4M annual revenue (+40% YoY)",
        "current_suggestion": "Drove $2.4M annual revenue (+40% YoY)",
        "user_message": "actually monthly",
        "history": [],
    }
    r = client_with_chat.post("/resume/bullet-chat", json=body)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")
    lines = [json.loads(ln) for ln in r.text.splitlines() if ln.strip()]
    assert lines[0]["type"] == "progress"
    assert lines[-1]["type"] == "result"
    assert lines[-1]["data"]["mode"] == "rewrite"
    assert lines[-1]["data"]["proposed_text"] == "Led $2.4M monthly revenue"


def test_bullet_chat_rejects_empty_user_message(client_with_chat) -> None:
    body = {
        "issue_id": "iss_1",
        "original_text": "x",
        "baseline_suggestion": "y",
        "current_suggestion": "y",
        "user_message": "   ",
        "history": [],
    }
    r = client_with_chat.post("/resume/bullet-chat", json=body)
    assert r.status_code == 400
