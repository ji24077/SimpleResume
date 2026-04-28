"""Bullet chat (per-issue push-back) request/response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BulletChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class BulletChatRequest(BaseModel):
    issue_id: str
    original_text: str
    # Frozen reviewer-vetted baseline (issue.suggested_text), never mutated.
    # Falls back to current_suggestion when client hasn't been updated yet.
    baseline_suggestion: str = ""
    # Mutating display-only suggestion. Sent for backward compat / future use,
    # but the service intentionally does NOT trust this as fact-source.
    current_suggestion: str
    user_message: str
    history: list[BulletChatMessage] = Field(default_factory=list)
    section_id: str | None = None
    bullet_id: str | None = None
    severity: str | None = None
    category: str | None = None


class BulletChatResult(BaseModel):
    """Two-mode response.

    - mode="rewrite": proposed_text is a refined bullet; assistant_message
      explains the change in one sentence.
    - mode="clarify": proposed_text is empty; assistant_message is a
      clarifying question asking the user for a missing fact.
    """

    mode: Literal["rewrite", "clarify"] = "rewrite"
    proposed_text: str = ""
    assistant_message: str
