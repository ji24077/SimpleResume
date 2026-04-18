"""Backward-compatible shim — real helpers live in resume_service.routers._helpers."""

from resume_service.routers._helpers import *  # noqa: F401,F403
from resume_service.routers._helpers import (  # noqa: F401 — explicit re-exports
    GenerateResponse,
    _coerce_any_response,
    _coerce_generate_response,
    _inject_preview_coaching_from_previous,
    _parse_page_policy,
    _parse_preview_coaching,
    attempt_llm_latex_compile_fix,
    repair_json,
)
from resume_service.services.pdf_service import extract_text  # noqa: F401
from resume_service.models import (  # noqa: F401
    CoachingItem,
    CoachingSection,
    GenerateJsonBody,
    PagePolicy,
    PreviewSection,
)
