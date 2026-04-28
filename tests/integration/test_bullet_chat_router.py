"""Integration: /resume/bullet-chat NDJSON streaming behind FEATURE_BULLET_CHAT."""

from __future__ import annotations

import json
import os

import pytest


def _build_app_with_chat_enabled():
    """Re-import the app with FEATURE_BULLET_CHAT=true so the router is included."""
    os.environ["FEATURE_BULLET_CHAT"] = "true"
    # Force-reload the modules whose state depends on the env var.
    import importlib

    import resume_service.config as cfg

    importlib.reload(cfg)
    import resume_service.app as app_module

    importlib.reload(app_module)
    return app_module.app


@pytest.fixture
def client_with_chat(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("FEATURE_BULLET_CHAT", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    app = _build_app_with_chat_enabled()

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
