"""POST /resume/bullet-chat — multi-turn push-back on a single review issue's rewrite."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from resume_service.config import settings
from resume_service.models.bullet_chat import BulletChatRequest
from resume_service.services.bullet_chat_service import refine_bullet
from resume_service.services.openai_service import get_openai_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resume/bullet-chat")
def bullet_chat(body: BulletChatRequest):
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not set")
    if not body.user_message.strip():
        raise HTTPException(status_code=400, detail="user_message is required")
    if not body.original_text.strip():
        raise HTTPException(status_code=400, detail="original_text is required")

    client = get_openai_client()

    # Frozen reviewer-vetted baseline. Falls back through current_suggestion →
    # original_text so older clients without the new field still work.
    baseline = body.baseline_suggestion or body.current_suggestion or body.original_text

    def ndjson_iter():
        try:
            for ev in refine_bullet(
                client=client,
                original_text=body.original_text,
                baseline_suggestion=baseline,
                user_message=body.user_message,
                history=body.history,
                severity=body.severity,
                category=body.category,
            ):
                yield (json.dumps(ev, ensure_ascii=False) + "\n").encode("utf-8")
        except HTTPException as he:
            err = {"type": "error", "detail": str(he.detail), "status_code": he.status_code}
            yield (json.dumps(err, ensure_ascii=False) + "\n").encode("utf-8")

    return StreamingResponse(ndjson_iter(), media_type="application/x-ndjson; charset=utf-8")
