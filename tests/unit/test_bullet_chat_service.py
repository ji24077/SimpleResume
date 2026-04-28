"""Unit tests for bullet_chat_service.refine_bullet (v1.1: clarify + audit)."""

from __future__ import annotations

import json
from types import SimpleNamespace

from resume_service.models.bullet_chat import BulletChatMessage
from resume_service.services.bullet_chat_service import refine_bullet


class _FakeChat:
    def __init__(self, contents: list[str]):
        self._contents = list(contents)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self._contents.pop(0) if self._contents else "{}"
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class _FakeClient:
    """Fake OpenAI client. Pass an ordered list of response payloads."""

    def __init__(self, contents: list[str]):
        self.chat = SimpleNamespace(completions=_FakeChat(contents))

    @property
    def calls(self) -> list[dict]:
        return self.chat.completions.calls  # type: ignore[no-any-return]


def _drain(events):
    return list(events)


def test_clean_rewrite_emits_progress_then_result() -> None:
    payload = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "- Drove $2.4M monthly revenue",
            "assistant_message": "Switched to monthly cadence.",
        }
    )
    client = _FakeClient([payload])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Increased revenue by $2.4M annually",
            baseline_suggestion="Drove $2.4M annual revenue",
            user_message="actually monthly, not annual",
            history=[],
        )
    )
    assert events[0]["type"] == "progress"
    assert events[-1]["type"] == "result"
    data = events[-1]["data"]
    assert data["mode"] == "rewrite"
    assert data["proposed_text"] == "Drove $2.4M monthly revenue"
    assert data["assistant_message"] == "Switched to monthly cadence."
    # Single LLM call — no retry needed.
    assert len(client.calls) == 1


def test_clarify_mode_passes_through_with_empty_proposed() -> None:
    payload = json.dumps(
        {
            "mode": "clarify",
            "proposed_text": "",
            "assistant_message": "How much did response time improve by?",
        }
    )
    client = _FakeClient([payload])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Built data observability framework",
            baseline_suggestion="Built data observability framework for pipelines",
            user_message="re-add a metric",
            history=[],
        )
    )
    data = events[-1]["data"]
    assert data["mode"] == "clarify"
    assert data["proposed_text"] == ""
    assert "improve" in data["assistant_message"].lower()


def test_audit_violation_triggers_retry() -> None:
    """First response invents 20%; retry returns clean clarify."""
    bad = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "Improved response time by 20%",
            "assistant_message": "Added metric.",
        }
    )
    good = json.dumps(
        {
            "mode": "clarify",
            "proposed_text": "",
            "assistant_message": "What was the actual improvement?",
        }
    )
    client = _FakeClient([bad, good])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Built data observability framework",
            baseline_suggestion="Built framework with SLA",
            user_message="re-add a metric",
            history=[],
        )
    )
    progresses = [e for e in events if e["type"] == "progress"]
    assert len(progresses) == 2  # initial + "rechecking facts"
    assert events[-1]["data"]["mode"] == "clarify"
    assert events[-1]["data"]["proposed_text"] == ""
    # Two LLM calls — one initial + one retry.
    assert len(client.calls) == 2
    # Retry's primer must mention the offending token.
    retry_primer = client.calls[1]["messages"][1]["content"]
    assert "20%" in retry_primer
    assert "AUDIT_VIOLATION" in retry_primer


def test_audit_failure_then_retry_also_invents_falls_back_hard() -> None:
    bad1 = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "Boosted by 20%",
            "assistant_message": "Done.",
        }
    )
    bad2 = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "Boosted by 35%",
            "assistant_message": "Better!",
        }
    )
    client = _FakeClient([bad1, bad2])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Built X",
            baseline_suggestion="Built X",
            user_message="add a metric",
            history=[],
        )
    )
    data = events[-1]["data"]
    assert data["mode"] == "clarify"
    assert data["proposed_text"] == ""
    assert "specific" in data["assistant_message"].lower() or "value" in data[
        "assistant_message"
    ].lower()


def test_user_provided_fact_in_message_passes_audit() -> None:
    """When the user explicitly provides '35%', the LLM may use it."""
    payload = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "Improved response time by 35%",
            "assistant_message": "Added the metric you provided.",
        }
    )
    client = _FakeClient([payload])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Built framework",
            baseline_suggestion="Built framework",
            user_message="response time improved by about 35%",
            history=[],
        )
    )
    assert events[-1]["data"]["mode"] == "rewrite"
    assert events[-1]["data"]["proposed_text"] == "Improved response time by 35%"
    # No retry — 35% is in the user message, so allowed.
    assert len(client.calls) == 1


def test_history_user_message_facts_carry_forward_into_allowed() -> None:
    """A fact provided in turn 1 should be allowed in turn 3."""
    payload = json.dumps(
        {
            "mode": "rewrite",
            "proposed_text": "Improved response time by 35% across SLA tier",
            "assistant_message": "Tightened around 35%.",
        }
    )
    client = _FakeClient([payload])
    history = [
        BulletChatMessage(role="user", content="response time was up 35%"),
        BulletChatMessage(role="assistant", content="Added 35%."),
    ]
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Built framework",
            baseline_suggestion="Built framework with SLA",
            user_message="now make it tighter",
            history=history,
        )
    )
    assert events[-1]["data"]["mode"] == "rewrite"
    assert len(client.calls) == 1


def test_message_assembly_includes_allowed_facts_block() -> None:
    payload = json.dumps(
        {"mode": "rewrite", "proposed_text": "ok", "assistant_message": "done"}
    )
    client = _FakeClient([payload])
    _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="Drove $2.4M annual revenue (+40% YoY)",
            baseline_suggestion="Drove $2.4M revenue (+40% YoY) at scale",
            user_message="shorter",
            history=[],
        )
    )
    primer = client.calls[0]["messages"][1]["content"]
    assert "ALLOWED_FACTS" in primer
    assert "$2.4M" in primer
    assert "40%" in primer
    assert "YoY" in primer
    assert "ORIGINAL" in primer
    assert "BASELINE_SUGGESTION" in primer


def test_handles_non_json_response() -> None:
    client = _FakeClient(["definitely not json"])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="orig",
            baseline_suggestion="baseline",
            user_message="hi",
            history=[],
        )
    )
    assert events[-1]["type"] == "error"
    assert events[-1]["status_code"] == 502


def test_empty_rewrite_text_coerced_to_clarify() -> None:
    payload = json.dumps(
        {"mode": "rewrite", "proposed_text": "", "assistant_message": "hmm"}
    )
    client = _FakeClient([payload])
    events = _drain(
        refine_bullet(
            client=client,  # type: ignore[arg-type]
            original_text="orig",
            baseline_suggestion="baseline",
            user_message="x",
            history=[],
        )
    )
    data = events[-1]["data"]
    assert data["mode"] == "clarify"
    assert data["proposed_text"] == ""
