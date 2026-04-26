"""Shared helpers used across routers."""

import json
import logging
import re
from typing import Any

from fastapi import HTTPException
from openai import OpenAI
from pydantic import ValidationError

from compile_pdf import (
    normalize_to_dhruv_template,
    sanitize_latex_for_overleaf,
    sanitize_unicode_for_latex,
)
from resume_service.config import settings
from prompts import (
    fixer_compile_system,
    revision_user_fix_compile,
    revision_user_fix_schema,
    structured_fixer_compile_system,
    structured_fixer_system,
)
from structured_resume import (
    ResumeSchemaError,
    build_latex_document,
    format_resume_validation_errors,
    parse_resume_data,
)
from resume_service.models import (
    CoachingItem,
    CoachingSection,
    GenerateResponse,
    PreviewSection,
)

logger = logging.getLogger(__name__)


def repair_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _parse_preview_coaching(data: dict[str, Any]) -> tuple[list[PreviewSection], list[CoachingSection]]:
    preview_raw = data.get("preview_sections") or []
    coaching_raw = data.get("coaching") or []

    preview_sections: list[PreviewSection] = []
    for p in preview_raw:
        if isinstance(p, dict):
            preview_sections.append(
                PreviewSection(
                    kind=str(p.get("kind", "experience")),
                    title=str(p.get("title", "")),
                    subtitle=p.get("subtitle"),
                    bullets=list(p.get("bullets") or []),
                )
            )

    coaching: list[CoachingSection] = []
    for c in coaching_raw:
        if isinstance(c, dict):
            items = []
            for it in c.get("items") or []:
                if isinstance(it, dict):
                    items.append(CoachingItem(why_better=str(it.get("why_better", ""))))
                else:
                    items.append(CoachingItem(why_better=str(it)))
            coaching.append(
                CoachingSection(
                    section_why=str(c.get("section_why", "")),
                    items=items,
                )
            )

    while len(coaching) < len(preview_sections):
        coaching.append(CoachingSection(section_why="", items=[]))
    for i, prev in enumerate(preview_sections):
        while len(coaching[i].items) < len(prev.bullets):
            coaching[i].items.append(CoachingItem(why_better=""))
        coaching[i].items = coaching[i].items[: len(prev.bullets)]

    return preview_sections, coaching


def _coerce_latex_document_response(data: dict[str, Any]) -> GenerateResponse:
    latex = data.get("latex_document") or data.get("latex") or ""
    if not latex or "\\documentclass" not in latex:
        raise HTTPException(
            status_code=502,
            detail="Model did not return a valid latex_document.",
        )
    latex = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(latex))
    )
    preview_sections, coaching = _parse_preview_coaching(data)
    return GenerateResponse(
        latex_document=latex,
        preview_sections=preview_sections,
        coaching=coaching,
    )


def _coerce_structured_attempt(
    data: dict[str, Any],
) -> tuple[GenerateResponse, dict[str, Any]]:
    rd_raw = data.get("resume_data")
    if not isinstance(rd_raw, dict):
        raise ResumeSchemaError(
            ["- resume_data: must be a JSON object"],
            data,
        )
    try:
        rd = parse_resume_data(rd_raw)
    except ValidationError as e:
        raise ResumeSchemaError(format_resume_validation_errors(e), data) from e
    try:
        latex = build_latex_document(rd)
    except ValueError as e:
        raise ResumeSchemaError([f"- document: {e}"], data) from e
    latex = sanitize_latex_for_overleaf(sanitize_unicode_for_latex(latex))
    preview_sections, coaching = _parse_preview_coaching(data)
    return (
        GenerateResponse(
            latex_document=latex,
            preview_sections=preview_sections,
            coaching=coaching,
        ),
        rd_raw,
    )


def _llm_fix_resume_schema(
    client: OpenAI,
    fixer_sys: str,
    model_response: dict[str, Any],
    schema_errors: list[str],
) -> dict[str, Any]:
    user = revision_user_fix_schema(
        model_response=model_response,
        schema_errors=schema_errors,
    )
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": fixer_sys},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.15,
        
    )
    raw = completion.choices[0].message.content or "{}"
    return repair_json(raw)


def _structured_coerce_pipeline(
    client: OpenAI | None,
    data: dict[str, Any],
    fixer_sys: str,
    log_en: list[str],
) -> tuple[GenerateResponse, dict[str, Any]]:
    work = data
    max_h = settings.resume_schema_heal_max if client is not None else 0
    for attempt in range(max_h + 1):
        try:
            return _coerce_structured_attempt(work)
        except ResumeSchemaError as e:
            if attempt >= max_h:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": "resume_data_schema_failed",
                        "schema_errors": e.errors,
                    },
                ) from None
            log_en.append(
                f"resume_data failed validation; schema self-heal ({attempt + 1}/{max_h})…"
            )
            work = _llm_fix_resume_schema(
                client, fixer_sys, e.model_response, e.errors
            )
    raise AssertionError("structured coerce pipeline unreachable")


def _coerce_any_response(
    data: dict[str, Any],
    *,
    client: OpenAI | None = None,
    fixer_sys: str = "",
    log_en: list[str] | None = None,
) -> tuple[GenerateResponse, dict[str, Any] | None]:
    if not settings.resume_structured_latex:
        return _coerce_latex_document_response(data), None
    fs = fixer_sys.strip() or structured_fixer_system()
    le = log_en or []
    return _structured_coerce_pipeline(client, data, fs, le)


def _coerce_generate_response(data: dict[str, Any]) -> GenerateResponse:
    r, _ = _coerce_any_response(data)
    return r


def attempt_llm_latex_compile_fix(
    client: OpenAI,
    *,
    tex_for_prompt: str,
    err_snippet: str,
) -> tuple[str | None, str | None]:
    user = revision_user_fix_compile(latex=tex_for_prompt, error_snippet=err_snippet)
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": fixer_compile_system()},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        
    )
    raw = completion.choices[0].message.content or "{}"
    try:
        data = repair_json(raw)
    except json.JSONDecodeError:
        logger.warning("compile heal: model returned invalid JSON")
        return None, None
    reason = data.get("reason") if isinstance(data.get("reason"), str) else None
    latex_out = (data.get("latex_document") or data.get("latex") or "").strip()
    if not latex_out or "\\documentclass" not in latex_out:
        return None, reason
    latex_out = sanitize_latex_for_overleaf(
        sanitize_unicode_for_latex(normalize_to_dhruv_template(latex_out))
    )
    return latex_out, reason


def _inject_preview_coaching_from_previous(
    data: dict[str, Any],
    prev: GenerateResponse | None,
) -> None:
    if prev is None:
        return
    ps = data.get("preview_sections")
    ch = data.get("coaching")
    if not ps:
        data["preview_sections"] = [p.model_dump() for p in prev.preview_sections]
    if not ch:
        data["coaching"] = [c.model_dump() for c in prev.coaching]


def _parse_page_policy(value: str | None):
    from resume_service.models.resume import PagePolicy
    if (value or "").strip().lower() in ("allow_multi", "multi", "allow_multiple"):
        return "allow_multi"
    return "strict_one_page"
