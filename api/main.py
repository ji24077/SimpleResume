"""SimpleResume API — backward-compatible entry point.

Start with:  uvicorn main:app --reload --host 0.0.0.0 --port 8000

The real application factory lives in resume_service.app; this module
re-exports everything that tests and tooling expect to find here.
"""

from resume_service.app import app  # noqa: F401

from resume_service.config import settings, Settings  # noqa: F401
from resume_service.routers._helpers import (  # noqa: F401
    GenerateResponse,
    _parse_preview_coaching,
    repair_json,
)
from resume_service.services.pdf_service import extract_text  # noqa: F401
