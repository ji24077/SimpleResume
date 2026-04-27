"""Resume parse service: raw text → ResumeData JSON via single LLM call.

Used by the verify-parse stage (POST /resume/parse). Distinct from the
generator: this LLM is told to copy fields verbatim, never rewrite. Schema
self-heal loop bounded by ``RESUME_SCHEMA_HEAL_MAX``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from features.generation.structured_resume import (
    ResumeData,
    format_resume_validation_errors,
    parse_resume_data,
)
from prompts import (
    build_parse_user_message,
    parser_system,
    revision_user_fix_schema,
    structured_fixer_system,
)
from resume_service.config import settings
from resume_service.routers._helpers import repair_json

logger = logging.getLogger(__name__)


class ParseError(RuntimeError):
    """Raised when the parser LLM cannot produce valid resume_data after self-heal."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def _call_parser_llm(client: OpenAI, raw: str) -> dict[str, Any]:
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": parser_system()},
            {"role": "user", "content": build_parse_user_message(raw)},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    content = completion.choices[0].message.content or "{}"
    return repair_json(content)


def _heal_schema(
    client: OpenAI,
    model_response: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    """Single-shot schema heal — re-prompt the structured fixer with the validation errors."""
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": structured_fixer_system()},
            {
                "role": "user",
                "content": revision_user_fix_schema(
                    model_response=model_response,
                    schema_errors=errors,
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    content = completion.choices[0].message.content or "{}"
    return repair_json(content)


def _drop_hallucinated_links(rd: ResumeData, raw: str) -> tuple[ResumeData, int]:
    """Remove header.links entries whose URL host (or full URL) doesn't appear
    in the raw source text. The parser LLM occasionally fabricates plausible
    looking URLs (`davidwang.com`, `github.com/jane`) when none was present;
    this is the safety net that keeps fake contact info from reaching the PDF.
    """
    if not rd.header.links:
        return rd, 0
    raw_lc = raw.lower()
    kept = []
    dropped = 0
    for link in rd.header.links:
        url = (link.url or "").strip()
        if not url:
            continue
        # Strip protocol + path for hostname-only match
        host = url
        if "://" in host:
            host = host.split("://", 1)[1]
        host = host.split("/", 1)[0].lower()
        if not host:
            dropped += 1
            continue
        if host in raw_lc or url.lower() in raw_lc:
            kept.append(link)
            continue
        # Allow generic "linkedin.com/in/<slug>" / "github.com/<slug>" only when
        # the slug also appears in the source.
        slug = ""
        if "://" in url:
            tail = url.split("://", 1)[1].split("/", 1)
            slug = tail[1].split("/", 1)[0].lower() if len(tail) > 1 else ""
        if slug and slug in raw_lc:
            kept.append(link)
            continue
        dropped += 1
    if dropped:
        rd.header.links = kept
    return rd, dropped


def extract_resume_data(client: OpenAI, raw: str) -> tuple[ResumeData, list[str]]:
    """Extract ``ResumeData`` from raw resume text.

    Returns (resume_data, warnings). Warnings is a best-effort list of human-
    readable notes about heal attempts or partial fields. Raises ``ParseError``
    if the schema cannot be satisfied within ``RESUME_SCHEMA_HEAL_MAX`` retries.
    """
    warnings: list[str] = []

    try:
        data = _call_parser_llm(client, raw)
    except json.JSONDecodeError as e:
        raise ParseError([f"Parser LLM returned invalid JSON: {e}"]) from e

    rd_raw = data.get("resume_data")
    if not isinstance(rd_raw, dict):
        # Some models drop the wrapper key; accept the bare object too.
        if "header" in data and "skills" in data:
            rd_raw = data
        else:
            raise ParseError(["Parser LLM did not return a 'resume_data' object"])

    work = rd_raw
    last_response = data
    max_heal = settings.resume_schema_heal_max
    for attempt in range(max_heal + 1):
        try:
            rd_obj = parse_resume_data(work)
            rd_obj, dropped = _drop_hallucinated_links(rd_obj, raw)
            if dropped:
                warnings.append(
                    f"Dropped {dropped} header link(s) the model made up "
                    f"(host not found in source)."
                )
            return rd_obj, warnings
        except ValidationError as e:
            errors = format_resume_validation_errors(e)
            if attempt >= max_heal:
                raise ParseError(errors) from e
            warnings.append(
                f"resume_data failed validation; self-heal attempt {attempt + 1}/{max_heal}"
            )
            try:
                fixed = _heal_schema(
                    client,
                    {"resume_data": work, **{k: v for k, v in last_response.items() if k != "resume_data"}},
                    errors,
                )
            except json.JSONDecodeError:
                logger.warning("Parse heal returned invalid JSON; giving up")
                raise ParseError(errors) from e
            new_rd = fixed.get("resume_data")
            if isinstance(new_rd, dict):
                work = new_rd
                last_response = fixed
            elif "header" in fixed and "skills" in fixed:
                work = fixed
                last_response = {"resume_data": fixed}
            else:
                raise ParseError(errors) from e
    raise AssertionError("parse heal loop unreachable")
